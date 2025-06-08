from cip_server.config import get_config
from cip_server.daemon.daemon_pb2_grpc import PipelineExecutorStub
import grpc


async def get_pipeline_executor_stub():
    async with grpc.aio.insecure_channel(get_config().daemon.channel) as channel:
        stub = PipelineExecutorStub(channel)
        yield stub