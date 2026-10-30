"""Initial provenance, passage and financial fact schema."""

from alembic import op
from researchdesk.db import Base

revision = "0001"
down_revision = None


def upgrade():
    Base.metadata.create_all(op.get_bind())
    op.execute("CREATE INDEX passage_search ON passages USING gin(to_tsvector('english', text))")


def downgrade():
    Base.metadata.drop_all(op.get_bind())
