from typing import List
import uuid
from cip_server.daemon.daemon_pb2_grpc import PipelineExecutorStub
from cip_server.daemon.daemon_pb2 import PipelineExecutionRequest
from cip_server.models.pipelines import PipelineExecution
from cip_server.models.results import JobResult
from cip_server.models.schemas import JobResultSchema, PipelineExecutionSchema
from cip_server.utils.daemon import get_pipeline_executor_stub
from cip_server.utils.database import get_session
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends


pipeline_router = APIRouter(tags=["Pipeline Executions"])

@pipeline_router.get("/pipeline/{pipeline_id}", 
                     summary="Get a pipeline execution object", 
                     description="Retrieve all the details for a pipeline execution with the given id",
                     response_model=PipelineExecutionSchema)
async def get_pipeline(pipeline_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    pipeline_execution = await session.get(PipelineExecution, pipeline_id)
    return pipeline_execution

@pipeline_router.get("/pipeline",
                     summary="Get pipeline executions",
                     description="Retrieve a paginated list of pipeline execution objects",
                     response_model=List[PipelineExecutionSchema])
async def get_pipelines(session: AsyncSession = Depends(get_session), limit: int = 5, offset: int = 0):
    return [execution for execution in await session.scalars(select(PipelineExecution).limit(limit).offset(offset))]
    
@pipeline_router.get("/pipeline/{pipeline_id}/result/{index}",
                     summary="Get a job result object",
                     description="Retrieve the result of a job in a pipeline using their id and index",
                     response_model=JobResultSchema)
async def get_job_result(pipeline_id: uuid.UUID, index: int, session: AsyncSession = Depends(get_session)):
    pipeliene_execution = await session.get(PipelineExecution, pipeline_id, options=[selectinload(PipelineExecution.job_results)])
    return pipeliene_execution.job_results[index]

@pipeline_router.get("/pipeline/{pipeline_id}/result",
                     summary="Get job results for a pipeline execution",
                     description="Retrieve a paginated list of job result objects belonging to a pipeline",
                     response_model=List[JobResultSchema])
async def get_job_results(pipeline_id: uuid.UUID, session: AsyncSession = Depends(get_session), limit: int = 5, offset: int = 0):
    return [result for result in await session.scalars(select(JobResult).where(JobResult.execution_id == pipeline_id).limit(limit).offset(offset))]

@pipeline_router.get("/result/{job_result_id}",
                     summary="Get a job result object",
                     description="Retrieve a job result using its id",
                     response_model=JobResultSchema)
async def get_job_result_by_id(job_result_id: int, session: AsyncSession = Depends(get_session)):
    job_result = await session.get(JobResult, job_result_id)
    return job_result

@pipeline_router.post("/pipeline",
                      summary="Create a new pipeline execution",
                      description="Run the pipeline defined in the repository at the given url and at the point of the given commit. Returns the unique id of the new pipeline")
async def create_pipeline(git_url: str, commit_hash: str, stub: PipelineExecutorStub = Depends(get_pipeline_executor_stub)):
    response = await stub.ExecutePipeline(PipelineExecutionRequest(git_url=git_url, commit_hash=commit_hash))
    return response.pipeline_execution_id