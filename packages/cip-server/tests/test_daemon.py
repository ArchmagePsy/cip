import asyncio
import multiprocessing
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path

import grpc
import pytest
from cip_server.daemon import daemon_pb2_grpc
from cip_server.daemon.daemon_pb2 import PipelineExecutionRequest
from cip_server.daemon.daemon_pb2_grpc import PipelineExecutorStub
from cip_server.daemon.main import PipelineExecutionDaemon, logger
from cip_server.models.base import Base
from cip_server.models.pipelines import PipelineExecution, PipelineStatus
from git import Repo
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer


# we must use the spawn method for testing as we cannot fork a process on a separate thread as it could lead to unknown behaviour
multiprocessing.set_start_method("spawn")

logger.setLevel("INFO")
postgres = PostgresContainer(username="test_user", password="pass1234", dbname="pipeline_database")

@pytest.fixture(scope="module", autouse=True)
def pipeline_database_engine(request):

    postgres.start()

    def cleanup():
        postgres.stop()

    request.addfinalizer(cleanup)

    engine = create_engine(postgres.get_connection_url())
    Base.metadata.create_all(engine)

    return engine

@pytest.fixture(scope="module")
def pipeline_database_session(pipeline_database_engine):
    return sessionmaker(pipeline_database_engine)

@pytest.fixture(scope="module")
def pipeline_daemon(request, pipeline_database_engine):
    daemon = PipelineExecutionDaemon(
        database_host=postgres.get_container_host_ip(),
        database_port=postgres.get_exposed_port(5432),
        database_user=postgres.username,
        database_password=postgres.password,
        database_name=postgres.dbname
    )

    # create a new event loop to run the test daemon in
    loop = asyncio.new_event_loop()

    async def daemon_test_main():
        """
        Because the daemon itself uses signal handlers which can only be added to event loops
        in the main thread we have to make a copy of the daemon's main method without the signal
        handling (pytest will shutdown the daemon once the tests are complete anyway).
        """
        logger.info("Starting Pipeline Execution Daemon")

        server = grpc.aio.server()
        daemon_pb2_grpc.add_PipelineExecutorServicer_to_server(daemon, server)
        server.add_insecure_port(f"{daemon.host}:{daemon.port}")

        logger.info("Starting async server for RPC")
        await server.start()

        await daemon.shutdown.wait()

        logger.info("Shutting down server")
        await server.stop(grace=None)
        
        daemon.process_pool.shutdown(cancel_futures=True)
        logger.info("Process pool shutdown")
        
        await daemon.async_db_engine.dispose()
        logger.info("Database engine disposed")

    def daemon_test_loop():
        """this function begins the test daemon's loop, we define it here to enclose it in a separate thread later"""
        asyncio.set_event_loop(loop)
        loop.run_until_complete(daemon_test_main())

    # here we place the test daemon on a separate thread
    daemon_thread = threading.Thread(target=daemon_test_loop)
    daemon_thread.start()

    # we want to wait for the daemon to be ready to accept connections to ensure there is no race condition for our tests
    test_channel = grpc.insecure_channel(f"{daemon.host}:{daemon.port}")
    while test_channel._channel.check_connectivity_state(True) != grpc.ChannelConnectivity.READY.value[0]:
        time.sleep(1)

    test_channel.close()
    
    def cleanup():
        """this cleanup function injects the call to stop the daemon into its event loop and then attempts to join the thread"""
        loop.call_soon_threadsafe(daemon.stop)
        daemon_thread.join()

    request.addfinalizer(cleanup)

    return daemon

def pipeline_execution_test(pipeline_daemon: PipelineExecutionDaemon, pipeline_database_session: sessionmaker, pipeline: str, test):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            git_repo = Repo.init(temp_dir)
            Path(os.path.join(temp_dir, "cip.toml")).touch()
            Path(os.path.join(temp_dir, ".cip.py")).write_text(pipeline)

            git_repo.git.add(all=True)
            git_repo.git.commit("-m", "successful pipeline")

            with grpc.insecure_channel(f"{pipeline_daemon.host}:{pipeline_daemon.port}") as channel:
                stub = PipelineExecutorStub(channel)
                pipeline_execution_response = stub.ExecutePipeline(PipelineExecutionRequest(git_url=(url := os.path.join(temp_dir, ".git")), commit_hash=git_repo.head.commit.hexsha))

            with pipeline_database_session() as session:
                pipeline_execution = session.get(PipelineExecution, uuid.UUID(pipeline_execution_response.pipeline_execution_id))
                
                assert pipeline_execution.commit_hash == git_repo.head.commit.hexsha
                assert pipeline_execution.git_url == url

                test(session, pipeline_execution)
    finally:
        git_repo.close()

def test_pipeline_execution_success(pipeline_daemon, pipeline_database_session):

    def pipeline_success_test(session, pipeline_execution):
        while pipeline_execution.status != PipelineStatus.FINISHED:
            time.sleep(1)
            session.refresh(pipeline_execution)

        assert pipeline_execution.status == PipelineStatus.FINISHED
        assert pipeline_execution.job_results[0].result
    
    pipeline_execution_test(pipeline_daemon, pipeline_database_session, """
from cip_core.pipelines import Pipeline
from typing import Dict

default = Pipeline()

@default.test.success.step
def successful_step(context: Dict):
    return True
    """, pipeline_success_test)

def test_pipeline_execution_failure(pipeline_daemon, pipeline_database_session):
    def pipeline_failure_test(session, pipeline_execution):
        while pipeline_execution.status != PipelineStatus.FINISHED:
            time.sleep(1)
            session.refresh(pipeline_execution)

        assert pipeline_execution.status == PipelineStatus.FINISHED
        assert not pipeline_execution.job_results[0].result
    
    pipeline_execution_test(pipeline_daemon, pipeline_database_session, """
from cip_core.pipelines import Pipeline
from typing import Dict

default = Pipeline()

@default.test.failure.step
def failed_step(context: Dict):
    return False
    """, pipeline_failure_test)

def test_pipeline_execution_error(pipeline_daemon, pipeline_database_session):
    def pipeline_error_test(session, pipeline_execution):
        while pipeline_execution.status != PipelineStatus.ERROR:
            time.sleep(1)
            session.refresh(pipeline_execution)

        assert pipeline_execution.status == PipelineStatus.ERROR
        assert pipeline_execution.error == "Exception('a test error')"
        assert not pipeline_execution.job_results
    
    pipeline_execution_test(pipeline_daemon, pipeline_database_session, """
from cip_core.pipelines import Pipeline
from typing import Dict

default = Pipeline()

@default.test.error.step
def error_step(context: Dict):
    raise Exception("a test error")
    """, pipeline_error_test)