"""Per-user opportunities + generated ATS CVs.

Two changes:

1. ``opportunities.source_url`` was globally UNIQUE, which made the product
   single-user by construction: once one candidate stored a job, no other
   candidate could store their own scored copy of it. Uniqueness moves to
   ``(user_id, source_url)``, with a plain index left on ``source_url``.
   ``quality_score`` / ``source_reliability_score`` / ``verification_confidence``
   also lose their optimistic defaults so an unverified posting stops looking
   verified.

2. New ``generated_cvs`` table holding ATS-optimised CVs produced by
   CVBuilderAgent.

Revision ID: 002_multiuser_and_generated_cvs
Revises: 001_initial_schema
Create Date: 2026-09-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "002_multiuser_and_generated_cvs"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None

UNIQUE_NAME = "uq_opportunity_user_source_url"
INDEX_NAME = "ix_opportunities_source_url"


def _postgres_unique_constraints_on(bind, table: str, column: str) -> list[str]:
    """Names of single-column UNIQUE constraints/indexes covering `column`."""
    rows = bind.execute(
        sa.text(
            """
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_attribute att
              ON att.attrelid = rel.oid AND att.attnum = ANY (con.conkey)
            WHERE rel.relname = :table
              AND con.contype = 'u'
              AND array_length(con.conkey, 1) = 1
              AND att.attname = :column
            """
        ),
        {"table": table, "column": column},
    ).fetchall()
    return [r[0] for r in rows]


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    inspector = sa.inspect(bind)
    has_opportunities = "opportunities" in inspector.get_table_names()

    if has_opportunities:
        existing_uniques = {uc.get("name") for uc in inspector.get_unique_constraints("opportunities")}

        if dialect == "postgresql":
            for name in _postgres_unique_constraints_on(bind, "opportunities", "source_url"):
                op.drop_constraint(name, "opportunities", type_="unique")
            # A bare unique *index* (rather than constraint) is also possible.
            for ix in inspector.get_indexes("opportunities"):
                if ix.get("unique") and ix.get("column_names") == ["source_url"]:
                    op.drop_index(ix["name"], table_name="opportunities")

            if UNIQUE_NAME not in existing_uniques:
                op.create_unique_constraint(
                    UNIQUE_NAME, "opportunities", ["user_id", "source_url"]
                )
        else:
            # SQLite cannot drop an inline unnamed UNIQUE, so the table is
            # recreated. batch_alter_table copies the data for us.
            with op.batch_alter_table(
                "opportunities",
                recreate="always",
                table_kwargs={"sqlite_autoincrement": False},
            ) as batch:
                batch.create_unique_constraint(UNIQUE_NAME, ["user_id", "source_url"])

        # Drop the "looks verified by default" values.
        with op.batch_alter_table("opportunities") as batch:
            for col in ("quality_score", "source_reliability_score", "verification_confidence"):
                batch.alter_column(col, server_default=None, existing_type=sa.Integer())
            for col in ("safety_status", "freshness_status"):
                batch.alter_column(col, server_default=None, existing_type=sa.String(50))

        existing_indexes = {ix["name"] for ix in sa.inspect(bind).get_indexes("opportunities")}
        if INDEX_NAME not in existing_indexes:
            op.create_index(INDEX_NAME, "opportunities", ["source_url"])

    op.create_table(
        "generated_cvs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("opportunity_id", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("label", sa.String(255)),
        sa.Column("target_title", sa.String(255)),
        sa.Column("target_company", sa.String(255)),
        sa.Column("content_text", sa.Text, nullable=False),
        sa.Column("sections", sa.JSON),
        sa.Column("cover_letter", sa.Text),
        sa.Column("ats_score", sa.Integer, server_default="0"),
        sa.Column("ats_breakdown", sa.JSON),
        sa.Column("keywords_matched", sa.JSON),
        sa.Column("keywords_missing", sa.JSON),
        sa.Column("format_warnings", sa.JSON),
        sa.Column("generator", sa.String(50), server_default="template"),
        sa.Column("ai_provider", sa.String(50)),
        sa.Column("docx_path", sa.Text),
        sa.Column("pdf_path", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_generated_cvs_user_id", "generated_cvs", ["user_id"])
    op.create_index("ix_generated_cvs_opportunity_id", "generated_cvs", ["opportunity_id"])
    op.create_index("ix_generated_cvs_user_created", "generated_cvs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_generated_cvs_user_created", table_name="generated_cvs")
    op.drop_index("ix_generated_cvs_opportunity_id", table_name="generated_cvs")
    op.drop_index("ix_generated_cvs_user_id", table_name="generated_cvs")
    op.drop_table("generated_cvs")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "opportunities" not in inspector.get_table_names():
        return

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("opportunities")}
    if INDEX_NAME in existing_indexes:
        op.drop_index(INDEX_NAME, table_name="opportunities")

    with op.batch_alter_table("opportunities", recreate="always") as batch:
        batch.drop_constraint(UNIQUE_NAME, type_="unique")
        batch.create_unique_constraint("uq_opportunities_source_url", ["source_url"])
