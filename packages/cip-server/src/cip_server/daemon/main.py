import argparse
import asyncio
import atexit
import logging
import os
import runpy
import signal
import tempfile
import tomllib
import uuid
from concurrent.futures import CancelledError, Future, ProcessPoolExecutor
from typing import Dict

from cip_server.config import CipServerConfig
import grpc
from cip_core.pipelines import BasePipeline
from cip_server.daemon import daemon_pb2_grpc
from cip_server.daemon.daemon_pb2 import PipelineExecutionResponse, PipelineExecutionRequest
from cip_server.daemon.daemon_pb2_grpc import PipelineExecutorServicer
from cip_server.models.pipelines import PipelineExecution, PipelineStatus
from cip_server.models.results import JobResult
from cip_server.utils.errors import CipServerException
from git import Repo
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


logging.basicConfig()
logger = logging.getLogger("PIPELINE EXECUTION DAEMON")

worker_session_factory = None

def checkout_project(git_url: str, commit_hash: str, to_path: os.PathLike):
    """
    Clones a git repository into a directory and checks out a particular commit.

    Args:
        git_url(str): the url of the git repository, can be any type of path or url that the system's git installation supports
        commit_hash(str): the hash of the commit to checkout on the repository
        to_path(PathLike): the path to the directory to clone the remote repository into

    Returns:
        Repo: the repo object for the repository we just cloned
    """
    logger.debug(f"Cloning project {git_url} to {to_path}")
    clone_repo = Repo.clone_from(git_url, to_path)
    logger.debug(F"Checking out commit {commit_hash} of {os.path.basename(clone_repo.working_tree_dir)} repository")
    clone_repo.git.checkout(commit_hash)

    return clone_repo

def find_pipeline(project_path: os.PathLike, config_path: os.PathLike):
    """
    Looks for a pipeline object in the project.

    This method looks for a toml config file at the specified location from the project's root directory. It looks for the "pipeline-path" parameter
    and runs the python program it points to (.cip.py if not specified) it then extracts the first pipeline object it finds and returns it.

    Args:
        project_path(PathLike): the path to the root of the project
        config_path(PathLike): the path from the root of the project to the toml file containing the config

    Returns:
        BasePipeline: the pipeline object found, None if no pipeline object is found
        Dict[str, Any]: the dictionary representing the config file that was parsed, to be used as the pipeline's context
    """
    logger.debug(f"Loading CIP config from {os.path.basename(project_path)} project")
    with open(os.path.join(project_path, config_path), "rb") as config_file:
        config = tomllib.load(config_file)
        pipeline_path = config.get("pipeline-path", ".cip.py")

    context = config.get("context", {})
    logger.debug(f"Loading pipeline file {pipeline_path}")
    pipeline_globals = runpy.run_path(os.path.join(project_path, pipeline_path))
    pipeline = next((value for value in pipeline_globals.values() if isinstance(value, BasePipeline)), None)

    return pipeline, context

def execute_pipeline(pipeline_id: uuid.UUID):
        """
        Execute a pipeline.

        This method is run by the worker processes and is responsible for creating a temporary directory to checkout the project to
        then finding its pipeline and executing it all while updating its entry in the database.

        Args:
            pipeline_id(UUID): the id of the pipeline execution to process, the worker expects that this will already have been created
        
        Returns:
            Dict[str, bool]: the results of the pipeline where each key is a job name and the value is True or False for pass or fail
        """
        if worker_session_factory is None: 
            raise CipServerException("No database session factory was found")
        
        with worker_session_factory() as session:

            pipeline_execution = session.get(PipelineExecution, pipeline_id)

            with tempfile.TemporaryDirectory(prefix="pipeline_", suffix=f"_{pipeline_execution.commit_hash}") as pipeline_temp_dir:
                checkpoint_cwd = os.getcwd()
                clone_repo = None
                try:
                    logger.debug(f"Temporary directory {pipeline_temp_dir} created")
                    logger.info("Checking out project")
                    clone_repo = checkout_project(pipeline_execution.git_url, pipeline_execution.commit_hash, pipeline_temp_dir)
                    logger.info("Looking for pipeline")
                    pipeline, context = find_pipeline(clone_repo.working_tree_dir, "cip.toml")
                    
                    if pipeline is None:
                        raise CipServerException(f"No pipeline found in {pipeline_execution.git_url} project")
                    
                    logger.debug(f"Switching to project directory {clone_repo.working_tree_dir}")
                    
                    os.chdir(clone_repo.working_tree_dir)
                    update_pipeline_status(session, pipeline_execution, PipelineStatus.RUNNING)
                    logger.info("Executing pipeline")
                    pipeline_results = {job.name: result for job, result in pipeline.run(context).items()}
                    return pipeline_results
                finally:
                    os.chdir(checkpoint_cwd)
                    if clone_repo is not None:
                        clone_repo.close()

def init_worker(connection_url: str):
    """
    Used to initialize the worker processes.

    Provides each worker process with a database engine and session factory that will cleanly be disposed of fowling its exit.

    Args:
        connection_url(str): the database connection url
    """
    global worker_session_factory
    db_engine = create_engine(connection_url)
    worker_session_factory = sessionmaker(db_engine)

    def __dispose_db_engine():
        db_engine.dispose()

    atexit.register(__dispose_db_engine)
    
def update_pipeline_status(session, pipeline_execution: PipelineExecution, status: PipelineStatus):
    """
    Update the status of a pipeline execution.

    Args:
        session: the sqlalchemy database session
        pipeline_execution(PipelineExecution): the pipeline execution object
        status(PipelineStatus): the status to update the pipeline execution to
    """
    pipeline_execution.status = status
    session.commit()
    session.refresh(pipeline_execution)
    
def publish_pipeline_result(session, pipeline_execution: PipelineExecution, results: Dict | None = None, status: PipelineStatus = PipelineStatus.FINISHED, error: str | None = None):
    """
    Publishes the job results of the pipeline execution.

    Args:
        session: the sqlalchemy database session
        pipeline_execution(PipelineExecution): the pipeline execution object
        results (Dict[str, bool]): a dictionary representing the results for the pipeline's jobs as key-value pairs of job name and result
        status(PipelineStatus): the status to update the pipeline execution to
        error(str): the error if any reported by this pipeline
    """
    pipeline_execution.status = status
    if results:
        job_results = []
        for job, result in results.items():
            job_results.append(JobResult(name = job, result = result, execution = pipeline_execution))

        session.add_all(job_results)
    if error:
        pipeline_execution.error = error

    session.commit()
    session.refresh(pipeline_execution)    
    
class PipelineExecutionDaemon(PipelineExecutorServicer):
    """
    This class is an implementation of the gRPC service for the pipeline execution daemon.
    """

    def __init__(self, database_host: str = "127.0.0.1", 
                    database_port: int = 5432, 
                    database_user: str = "user", 
                    database_password: str = "password", 
                    database_name: str = "database", 
                    host: str = "127.0.0.1", 
                    port: int = 3916, 
                    workers: int = 4):
        """
        Args:
            database_host(str): the host address of the postgres database
            database_port(int): the port to connect to the postgres database on
            database_user(str): the username to authenticate with the database as
            database_password(str): the password for the user of the postgres database
            database_name(str): the logical database name for the pipeline execution database
            host(str): the interface address for the daemon to listen on for RPC
            port(int): the port the daemon will bind to
            workers(int): the number of worker processes to execute pipelines on
        """
        super().__init__()
        
        self.host = host
        self.port = port
        self.database_host = database_host
        self.database_port = database_port
        self.database_user = database_user
        self.database_password = database_password
        self.database_name = database_name
        self.database_connection_suffix = f"{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_name}"
        self.process_pool = ProcessPoolExecutor(max_workers=workers, initializer=init_worker, initargs=(f"postgresql+psycopg2://{self.database_connection_suffix}",))
        self.async_db_engine = create_async_engine(f"postgresql+asyncpg://{self.database_connection_suffix}")
        self.async_session_factory = sessionmaker(bind=self.async_db_engine, expire_on_commit=False, class_=AsyncSession)
        logger.info("Database engine created")
        self.shutdown = asyncio.Event()

    async def ExecutePipeline(self, request: PipelineExecutionRequest, context):
        """
        The remote procedure to run pipeline executions.

        Args:
            request(PipelineExecutionRequest): the RPC request with the repository details for the pipeline to execute

        Returns:
            PipelineExecutionResponse: the response to the pipeline execution request containing the uuid for the newly created pipeline execution
        """
        logger.info("Receiving pipeline execution request")
        async with self.async_session_factory() as session:
            pipeline_execution = PipelineExecution(git_url = request.git_url, commit_hash = request.commit_hash)
            session.add(pipeline_execution)
            await session.commit()
            await session.refresh(pipeline_execution)
        
        pipeline_id = pipeline_execution.id    
        logger.info(f"Created pipeline execution {pipeline_id}")
        pipeline_execution_future = self.process_pool.submit(execute_pipeline, pipeline_id)
        
        def __publish_and_cleanup(future: Future[Dict]):
            db_engine = create_engine(f"postgresql+psycopg2://{self.database_connection_suffix}")
            session_factory = sessionmaker(db_engine)

            with session_factory() as session:
                try:
                    pipeline_execution = session.get(PipelineExecution, pipeline_id)

                    pipeline_execution_result = future.result()
                    publish_pipeline_result(session, pipeline_execution, results=pipeline_execution_result)
                    logger.info(f"Successfully completed pipeline {pipeline_id}")
                except CancelledError:
                    publish_pipeline_result(session, pipeline_execution, status=PipelineStatus.CANCELLED)
                    logger.info(f"Cancelled pipeline {pipeline_id}")
                except Exception as ex:
                    publish_pipeline_result(session, pipeline_execution, status=PipelineStatus.ERROR, error=repr(ex))
                    logger.error(f"Error executing pipeline {pipeline_id}", exc_info=True)
                finally:
                    db_engine.dispose()
        
        pipeline_execution_future.add_done_callback(__publish_and_cleanup)
        
        return PipelineExecutionResponse(pipeline_execution_id=str(pipeline_id))

    async def __main(self):
        logger.info("Starting Pipeline Execution Daemon")
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.stop)

        server = grpc.aio.server()
        daemon_pb2_grpc.add_PipelineExecutorServicer_to_server(self, server)
        server.add_insecure_port(f"{self.host}:{self.port}")

        logger.info("Starting async server for RPC")
        await server.start()

        await self.shutdown.wait()

        logger.info("Shutting down server")
        await server.stop(grace=5)
        
        self.process_pool.shutdown(cancel_futures=True)
        logger.info("Process pool shutdown")
        
        await self.async_db_engine.dispose()
        logger.info("Database engine disposed")

    def start(self):
        """
        Start the pipeline execution daemon
        """
        asyncio.run(self.__main())

    def stop(self):
        """
        Stop the pipeline execution daemon
        """
        self.shutdown.set()


if __name__ == "__main__":
    config = CipServerConfig()

    parser = argparse.ArgumentParser()
    postgres_args = parser.add_argument_group("postgres")
    postgres_args.add_argument("--postgres-host", type=str, default=config.database.host, help="The host for the postgres instance to connect to. Default is 127.0.0.1")
    postgres_args.add_argument("--postgres-port", type=int, default=config.database.port, help="The port that the postgres instance is listenning on. Default is 5432")
    postgres_args.add_argument("--postgres-user", type=str, default=config.database.username, help="The postgres username for the daemon to connect as")
    postgres_args.add_argument("--postgres-password", type=str, default=config.database.password, help="The postgres password for the daemon to use")
    postgres_args.add_argument("--postgres-database", type=str, default=config.database.name, help="The name of the postgres database to connect to")

    daemon_args = parser.add_argument_group("daemon")
    daemon_args.add_argument("--host", type=str, default=config.daemon.host, help="The host address the daemon should listen on. Default is 127.0.0.1")
    daemon_args.add_argument("--port", type=int, default=config.daemon.port, help="The port the daemon should accept connections from other processes on. Default is 3916")
    daemon_args.add_argument("--workers", type=int, default=config.daemon.workers, help="The number of worker processes the daemon should use to run pipelines in parrallel. Default is 4")
    daemon_args.add_argument("--log-level", type=str, help="The logging level for the daemon. If not specified the root logger's default level will be used")

    args = parser.parse_args()
    logger.setLevel(getattr(logging, str(args.log_level).upper(), logging.WARNING))

    pipeline_execution_daemon = PipelineExecutionDaemon(
        database_host=args.postgres_host, 
        database_port=args.postgres_port, 
        database_user=args.postgres_user, 
        database_password=args.postgres_password, 
        database_name=args.postgres_database, 
        host=args.host, 
        port=args.port, 
        workers=args.workers
    )
    pipeline_execution_daemon.start()