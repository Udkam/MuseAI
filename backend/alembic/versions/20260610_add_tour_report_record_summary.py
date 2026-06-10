"""Add record_summary column to tour_reports

Revision ID: 20260610_add_report_record_summary
Revises: 20260425_add_llm_trace_events
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_add_report_record_summary"
down_revision: str | None = "20260425_add_llm_trace_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tour_reports",
        sa.Column("record_summary", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tour_reports", "record_summary")
