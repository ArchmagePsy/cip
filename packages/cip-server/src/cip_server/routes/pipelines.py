import uuid
from cip_server.daemon.daemon_pb2_grpc import PipelineExecutorStub
from cip_server.daemon.daemon_pb2 import PipelineExecutionRequest
from cip_server.models.pipelines import PipelineExecution
from cip_server.utils.daemon import get_pipeline_executor_stub
from cip_server.utils.database import get_session
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends


pipeline_router = APIRouter()

@pipeline_router.get("/pipeline/{pipeline_id}")
async def get_pipeline(pipeline_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    pipeline_execution = await session.get(PipelineExecution, pipeline_id)
    return pipeline_execution
    
@pipeline_router.get("/pipeline/{pipeline_id}/result/{index}")
async def get_job_result(pipeline_id: uuid.UUID, index: int, session: AsyncSession = Depends(get_session)):
    pipeliene_execution = await session.get(PipelineExecution, pipeline_id, options=[selectinload(PipelineExecution.job_results)])
    return pipeliene_execution.job_results[index]

@pipeline_router.post("/pipeline")
async def create_pipeline(git_url: str, commit_hash: str, stub: PipelineExecutorStub = Depends(get_pipeline_executor_stub)):
    response = await stub.ExecutePipeline(PipelineExecutionRequest(git_url=git_url, commit_hash=commit_hash))
    return response.pipeline_execution_id