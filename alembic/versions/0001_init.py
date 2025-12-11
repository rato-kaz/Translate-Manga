"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2025-01-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="admin"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "series",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("series_id", sa.Integer(), sa.ForeignKey("series.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("page_count", sa.Integer()),
        sa.Column("json_path", sa.String(1024)),
        sa.Column("json_hash", sa.String(128)),
        sa.Column("rendered_zip_path", sa.String(1024)),
        sa.Column("rendered_zip_hash", sa.String(128)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "chapter_json",
        sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("chapters.id"), primary_key=True),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "chapter_summary",
        sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("chapters.id"), primary_key=True),
        sa.Column("summary_text", sa.Text()),
        sa.Column("character_registry", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("series_id", sa.Integer(), sa.ForeignKey("series.id")),
        sa.Column("chapter_id", sa.Integer(), sa.ForeignKey("chapters.id")),
        sa.Column("detail", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("audit_logs")
    op.drop_table("chapter_summary")
    op.drop_table("chapter_json")
    op.drop_table("chapters")
    op.drop_table("series")
    op.drop_table("users")

