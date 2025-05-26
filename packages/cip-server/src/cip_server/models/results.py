from cip_server.models.base import Base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid


class JobResult(Base):
    __tablename__ = "JobResults"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    result: Mapped[bool] = mapped_column(nullable=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("PipelineExecutions.id"))
    execution: Mapped["PipelineExecution"] = relationship(back_populates="job_results")