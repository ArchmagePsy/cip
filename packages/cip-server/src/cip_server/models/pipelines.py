from datetime import datetime, timezone
from typing import List
import uuid
import enum
from cip_server.models.results import JobResult
from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from cip_server.models.base import Base


def utcnow():
    return datetime.now(timezone.utc)

class PipelineStatus(enum.Enum):
    CANCELLED = "CANCELLED"
    FINISHED  = "FINISHED"
    PENDING   = "PENDING"
    RUNNING   = "RUNNING"
    ERROR     = "ERROR"

 
class PipelineExecution(Base):
    __tablename__ = "PipelineExecutions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow
    )

    last_update_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow
    )

    status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus),
        default=PipelineStatus.PENDING
    )

    error: Mapped[str] = mapped_column(nullable=True)

    git_url: Mapped[str] = mapped_column()
    commit_hash: Mapped[str] = mapped_column(String(40))

    job_results: Mapped[List["JobResult"]] = relationship(back_populates="execution")

    @property
    def duration(self):
        if self.status in [PipelineStatus.FINISHED, PipelineStatus.ERROR, PipelineStatus.CANCELLED]:
            return self.last_update_at - self.started_at
        else:
            return utcnow - self.started_at