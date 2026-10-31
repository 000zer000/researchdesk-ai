"""Retain explicit reporting basis; never infer restatements from recency."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    # 0001 uses current metadata on a clean install, whereas existing databases
    # need these columns. Both paths must produce the same schema.
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("facts")}
    if "reporting_basis" not in columns:
        op.add_column(
            "facts",
            sa.Column("reporting_basis", sa.String(), nullable=False, server_default="as_reported"),
        )
    if "restates_accession" not in columns:
        op.add_column("facts", sa.Column("restates_accession", sa.String(), nullable=True))


def downgrade():
    op.drop_column("facts", "restates_accession")
    op.drop_column("facts", "reporting_basis")
