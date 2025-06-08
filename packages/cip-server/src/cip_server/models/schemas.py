        
from datetime import datetime
import uuid
from cip_server.models.pipelines import PipelineStatus
from pydantic import BaseModel, Field


class PipelineExecutionSchema(BaseModel):
    id: uuid.UUID = Field(..., description="the unique identifier for the pipeline execution")
    started_at: datetime = Field(..., description="the time the pipeline was started in utc")
    last_update_at: datetime = Field(..., description="the time the pipeline was last updated in utc")
    status: PipelineStatus = Field(..., description="the status of the pipeline")
    error: str | None = Field(..., description="the error, if any, for the pipeline")
    git_url: str = Field(..., description="the git url for the pipeline's repository")
    commit_hash: str = Field(..., description="the commit hash that was checked out to run the pipeline")

class JobResultSchema(BaseModel):
    id: int = Field(..., description="the id of this job result")
    name: str = Field(..., description="the name of the job this result corresponds to")
    result: bool | None = Field(..., description="the result of the job")
    execution_id: uuid.UUID = Field(..., description="the unique identifier of the pipeline this job belongs to")
