"""Add created_by_email and created_by_name to documentmodel

Revision ID: b1c2d3e4f5a6
Revises: 4a32bcad2197
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = '4a32bcad2197'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('documentmodel', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by_email', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))
        batch_op.add_column(sa.Column('created_by_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False, server_default=''))


def downgrade() -> None:
    with op.batch_alter_table('documentmodel', schema=None) as batch_op:
        batch_op.drop_column('created_by_name')
        batch_op.drop_column('created_by_email')
