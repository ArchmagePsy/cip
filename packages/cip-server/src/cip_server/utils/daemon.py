from cip_server.config import CipServerConfig
from cip_server.daemon.daemon_pb2_grpc import PipelineExecutorStub
import grpc


config = CipServerConfig()

async def get_pipeline_executor_stub():
    async with grpc.aio.insecure_channel(config.daemon.channel) as channel:
        stub = PipelineExecutorStub(channel)
        yield stub