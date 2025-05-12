"""create campground table

Revision ID: 219052922e7f
Revises: 
Create Date: 2025-05-12 12:11:08.814201

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '219052922e7f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass



def downgrade() -> None:
    """Downgrade schema."""
    pass
