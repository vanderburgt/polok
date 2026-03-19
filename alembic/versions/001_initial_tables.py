"""initial tables

Revision ID: 001
Revises:
Create Date: 2026-03-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "municipalities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cbs_code", sa.String(6), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "national_parties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "parties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("municipality_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("municipalities.id"), nullable=False),
        sa.Column("national_party_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("national_parties.id")),
        sa.Column("raw_name", sa.String(512), nullable=False),
        sa.Column("party_type", sa.Enum("affiliated", "independent", name="partytype"), nullable=False),
        sa.Column("is_coalition", sa.Boolean, default=False),
        sa.Column("kiesraad_list_number", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "party_websites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("party_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("status", sa.Enum("pending_review", "confirmed", "rejected", name="websitestatus"), default="pending_review"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "programs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("party_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("source_url", sa.String(1024)),
        sa.Column("file_type", sa.Enum("pdf", "html", name="filetype")),
        sa.Column("raw_text", sa.Text),
        sa.Column("word_count", sa.Integer),
        sa.Column("qc_method", sa.Enum("text", "vision", name="qcmethod")),
        sa.Column("qc_correct_term", sa.Boolean),
        sa.Column("qc_correct_municipality", sa.Boolean),
        sa.Column("qc_correct_party", sa.Boolean),
        sa.Column("qc_is_program", sa.Boolean),
        sa.Column("qc_notes", sa.Text),
        sa.Column("overall_quality", sa.Enum("pass", "fail", "uncertain", name="qualityresult")),
        sa.Column("qc_escalated", sa.Boolean, default=False),
        sa.Column("not_found", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed national parties
    national_parties = sa.table(
        "national_parties",
        sa.column("name", sa.String),
    )
    op.bulk_insert(national_parties, [
        {"name": "50PLUS"},
        {"name": "BBB"},
        {"name": "BVNL"},
        {"name": "CDA"},
        {"name": "ChristenUnie"},
        {"name": "D66"},
        {"name": "DENK"},
        {"name": "FvD"},
        {"name": "GroenLinks"},
        {"name": "GroenLinks-PvdA"},
        {"name": "JA21"},
        {"name": "Nieuw Sociaal Contract"},
        {"name": "Partij voor de Dieren"},
        {"name": "PVV"},
        {"name": "PvdA"},
        {"name": "SGP"},
        {"name": "SP"},
        {"name": "Volt"},
        {"name": "VVD"},
    ])


def downgrade() -> None:
    op.drop_table("programs")
    op.drop_table("party_websites")
    op.drop_table("parties")
    op.drop_table("national_parties")
    op.drop_table("municipalities")

    for enum_name in ["partytype", "websitestatus", "filetype", "qcmethod", "qualityresult"]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
