"""add quantity

Revision ID: eeb3d38d1850
Revises: 7579e66413e8
Create Date: 2024-10-24 20:01:05.999586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'eeb3d38d1850'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("article", sa.Column("quantity", sa.Integer, default=1))


def downgrade() -> None:
    op.drop_column("article", "quantity")