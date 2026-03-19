"""Program routes."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import verify_api_key
from app.models import Municipality, Party, Program, FileType, QualityResult

router = APIRouter(tags=["programmas"])
templates = Jinja2Templates(directory="app/templates")


async def _query_programs(
    db: AsyncSession,
    kwaliteit: str | None = None,
    zoek: str | None = None,
    type: str | None = None,
    min_woorden: int | None = None,
    max_woorden: int | None = None,
    pagina: int = 1,
    per_pagina: int = 50,
):
    query = select(Program).options(
        selectinload(Program.party).selectinload(Party.municipality),
        selectinload(Program.party).selectinload(Party.national_party),
    )

    if kwaliteit:
        query = query.where(Program.overall_quality == QualityResult(kwaliteit))
    if type:
        query = query.where(Program.file_type == FileType(type))
    if min_woorden is not None:
        query = query.where(Program.word_count >= min_woorden)
    if max_woorden is not None:
        query = query.where(Program.word_count <= max_woorden)
    if zoek:
        query = query.join(Program.party).join(Party.municipality).where(
            or_(
                Party.raw_name.ilike(f"%{zoek}%"),
                Municipality.name.ilike(f"%{zoek}%"),
            )
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Program.created_at.desc()).offset((pagina - 1) * per_pagina).limit(per_pagina)
    result = await db.execute(query)
    programs = result.scalars().all()

    return {
        "programmas": [
            {
                "id": str(p.id),
                "partij_id": str(p.party_id),
                "partij": p.party.raw_name if p.party else None,
                "gemeente": p.party.municipality.name if p.party and p.party.municipality else None,
                "landelijke_partij": p.party.national_party.name if p.party and p.party.national_party else None,
                "bron_url": p.source_url,
                "bestandstype": p.file_type.value if p.file_type else None,
                "woorden": p.word_count,
                "kwaliteit": p.overall_quality.value if p.overall_quality else None,
                "qc_juiste_termijn": p.qc_correct_term,
                "qc_juiste_gemeente": p.qc_correct_municipality,
                "qc_juiste_partij": p.qc_correct_party,
                "qc_is_programma": p.qc_is_program,
                "qc_notities": p.qc_notes,
                "qc_methode": p.qc_method.value if p.qc_method else None,
                "qc_geescaleerd": p.qc_escalated,
                "niet_gevonden": p.not_found,
            }
            for p in programs
        ],
        "totaal": total,
        "pagina": pagina,
        "per_pagina": per_pagina,
        "totaal_paginas": (total + per_pagina - 1) // per_pagina,
    }


async def _query_stats(db: AsyncSession):
    result = await db.execute(select(
        func.count(Program.id).label("total"),
        func.count().filter(Program.overall_quality == QualityResult.PASS).label("pass"),
        func.count().filter(Program.overall_quality == QualityResult.FAIL).label("fail"),
        func.count().filter(Program.overall_quality == QualityResult.UNCERTAIN).label("uncertain"),
        func.count().filter(Program.not_found == True).label("not_found"),
    ))
    row = result.one()
    total_parties = (await db.execute(select(func.count(Party.id)))).scalar() or 0
    return {
        "totaal_programmas": row[0],
        "goedgekeurd": row[1],
        "afgekeurd": row[2],
        "onzeker": row[3],
        "niet_gevonden": row[4],
        "totaal_partijen": total_parties,
    }


async def _get_text(program_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(select(Program).where(Program.id == program_id))
    program = result.scalar_one_or_none()
    if not program:
        return PlainTextResponse("Niet gevonden", status_code=404)
    return PlainTextResponse(program.raw_text or "Geen tekst beschikbaar")


# --- Public API (key required) ---

@router.get("/api/programmas", dependencies=[Depends(verify_api_key)])
async def api_list_programs(
    db: AsyncSession = Depends(get_db),
    kwaliteit: str | None = None, zoek: str | None = None,
    type: str | None = None, min_woorden: int | None = None,
    max_woorden: int | None = None, pagina: int = 1, per_pagina: int = 50,
):
    """Lijst van verkiezingsprogramma's met filters."""
    return await _query_programs(db, kwaliteit, zoek, type, min_woorden, max_woorden, pagina, per_pagina)


@router.get("/api/programmas/stats", dependencies=[Depends(verify_api_key)])
async def api_program_stats(db: AsyncSession = Depends(get_db)):
    """Statistieken van verkiezingsprogramma's."""
    return await _query_stats(db)


@router.get("/api/programmas/{program_id}/tekst", dependencies=[Depends(verify_api_key)])
async def api_get_program_text(program_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Volledige tekst van een verkiezingsprogramma."""
    return await _get_text(program_id, db)


# --- Internal endpoints for web UI (no key) ---

@router.get("/_data/programmas", include_in_schema=False)
async def internal_list_programs(
    db: AsyncSession = Depends(get_db),
    kwaliteit: str | None = None, zoek: str | None = None,
    type: str | None = None, min_woorden: int | None = None,
    max_woorden: int | None = None, pagina: int = 1, per_pagina: int = 50,
):
    return await _query_programs(db, kwaliteit, zoek, type, min_woorden, max_woorden, pagina, per_pagina)


@router.get("/_data/programmas/stats", include_in_schema=False)
async def internal_program_stats(db: AsyncSession = Depends(get_db)):
    return await _query_stats(db)


@router.get("/_data/programmas/{program_id}/tekst", include_in_schema=False)
async def internal_get_program_text(program_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _get_text(program_id, db)


# --- HTML page ---

@router.get("/programmas", response_class=HTMLResponse, include_in_schema=False)
async def programs_page(request: Request, db: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse("programs.html", {"request": request})
