"""SQLAlchemy models for Polok."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --- Enums ---

class PartyType(str, enum.Enum):
    affiliated = "affiliated"
    independent = "independent"


class WebsiteStatus(str, enum.Enum):
    pending_review = "pending_review"
    confirmed = "confirmed"
    rejected = "rejected"


class FileType(str, enum.Enum):
    pdf = "pdf"
    html = "html"


class QCMethod(str, enum.Enum):
    text = "text"
    vision = "vision"


class QualityResult(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    UNCERTAIN = "uncertain"


# --- Models ---

class Municipality(Base):
    __tablename__ = "municipalities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cbs_code: Mapped[str] = mapped_column(String(6), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parties: Mapped[list[Party]] = relationship(back_populates="municipality")


class NationalParty(Base):
    __tablename__ = "national_parties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parties: Mapped[list[Party]] = relationship(back_populates="national_party")


class Party(Base):
    __tablename__ = "parties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    municipality_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("municipalities.id"), nullable=False)
    national_party_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("national_parties.id"))
    raw_name: Mapped[str] = mapped_column(String(512), nullable=False)
    party_type: Mapped[PartyType] = mapped_column(Enum(PartyType), nullable=False)
    is_coalition: Mapped[bool] = mapped_column(Boolean, default=False)
    kiesraad_list_number: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    municipality: Mapped[Municipality] = relationship(back_populates="parties")
    national_party: Mapped[NationalParty | None] = relationship(back_populates="parties")
    websites: Mapped[list[PartyWebsite]] = relationship(back_populates="party")
    programs: Mapped[list[Program]] = relationship(back_populates="party")


class PartyWebsite(Base):
    __tablename__ = "party_websites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    party_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("parties.id"), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[WebsiteStatus] = mapped_column(Enum(WebsiteStatus), default=WebsiteStatus.pending_review)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    party: Mapped[Party] = relationship(back_populates="websites")


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    party_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("parties.id"), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024))
    file_type: Mapped[FileType | None] = mapped_column(Enum(FileType))
    raw_text: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    qc_method: Mapped[QCMethod | None] = mapped_column(Enum(QCMethod))
    qc_correct_term: Mapped[bool | None] = mapped_column(Boolean)
    qc_correct_municipality: Mapped[bool | None] = mapped_column(Boolean)
    qc_correct_party: Mapped[bool | None] = mapped_column(Boolean)
    qc_is_program: Mapped[bool | None] = mapped_column(Boolean)
    qc_notes: Mapped[str | None] = mapped_column(Text)
    overall_quality: Mapped[QualityResult | None] = mapped_column(
        Enum(QualityResult, values_callable=lambda e: [m.value for m in e])
    )
    qc_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    not_found: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    party: Mapped[Party] = relationship(back_populates="programs")
