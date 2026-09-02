"""GitHub integration (V0.2)

Revision ID: 002
Revises: 001
Create Date: 2026-09-02 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            nullable=True,
        )
        batch_op.add_column(sa.Column("github_id", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("github_username", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("github_access_token", sa.String(length=255), nullable=True))

    op.create_index(op.f("ix_users_github_id"), "users", ["github_id"], unique=True)

    op.create_table(
        "commits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sha", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("repo_name", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "sha", name="uq_commits_user_sha"),
    )
    op.create_index(op.f("ix_commits_id"), "commits", ["id"], unique=False)
    op.create_index(op.f("ix_commits_user_id"), "commits", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_commits_user_id"), table_name="commits")
    op.drop_index(op.f("ix_commits_id"), table_name="commits")
    op.drop_table("commits")
    op.drop_index(op.f("ix_users_github_id"), table_name="users")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("github_access_token")
        batch_op.drop_column("github_username")
        batch_op.drop_column("github_id")
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=255),
            nullable=False,
        )
