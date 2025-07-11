"""created pipeline executions and job results

Revision ID: 896714d15673
Revises: 
Create Date: 2025-05-24 12:24:56.468701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '896714d15673'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('JobResults',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('result', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('PipelineExecutions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('last_update_at', sa.DateTime(), nullable=False),
    sa.Column('status', sa.Enum('CANCELLED', 'FINISHED', 'PENDING', 'RUNNING', 'ERROR', name='pipelinestatus'), nullable=False),
    sa.Column('error', sa.String(), nullable=True),
    sa.Column('git_url', sa.String(), nullable=False),
    sa.Column('commit_hash', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('PipelineExecutions')
    op.drop_table('JobResults')
    # ### end Alembic commands ###
