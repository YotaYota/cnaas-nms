"""add job status ABORTING and start_arguments field to job to save starting arguments in history

Revision ID: 9d01bce3c835
Revises: 8a635012afa7
Create Date: 2020-11-02 10:03:03.293297

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "9d01bce3c835"
down_revision = "8a635012afa7"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("job", sa.Column("start_arguments", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.execute("COMMIT")
    op.execute("ALTER TYPE jobstatus ADD VALUE 'ABORTING' AFTER 'ABORTED'")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("job", "start_arguments")
    # ### end Alembic commands ###
