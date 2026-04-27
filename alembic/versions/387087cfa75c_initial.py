"""initial

Revision ID: 387087cfa75c
Revises: 4693537b72c3
Create Date: 2025-12-29 21:39:15.300898

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '387087cfa75c'
down_revision: Union[str, Sequence[str], None] = '4693537b72c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
