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


async def _gemeente_program_status(db: AsyncSession):
    """Return coverage per gemeente: total parties, parties with passing program."""
    result = await db.execute(
        select(
            Municipality.cbs_code,
            Municipality.name,
            func.count(Party.id.distinct()).label("totaal_partijen"),
            func.count(Party.id.distinct()).filter(
                Program.overall_quality == QualityResult.PASS
            ).label("met_programma"),
        )
        .outerjoin(Party, Party.municipality_id == Municipality.id)
        .outerjoin(Program, Program.party_id == Party.id)
        .group_by(Municipality.cbs_code, Municipality.name)
    )
    return [
        {
            "code": r.cbs_code,
            "naam": r.name,
            "totaal_partijen": r.totaal_partijen,
            "met_programma": r.met_programma,
            "dekking": round(r.met_programma / r.totaal_partijen, 2) if r.totaal_partijen > 0 else 0,
        }
        for r in result.all()
    ]


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


# --- Map data ---

@router.get("/_data/gemeenten/status", include_in_schema=False)
async def internal_gemeente_status(db: AsyncSession = Depends(get_db)):
    return await _gemeente_program_status(db)


@router.get("/api/gemeenten/status", dependencies=[Depends(verify_api_key)])
async def api_gemeente_status(db: AsyncSession = Depends(get_db)):
    """Programma-status per gemeente (CBS-code)."""
    return await _gemeente_program_status(db)


# --- DB dump download ---

@router.get("/_data/download/dump.sql", include_in_schema=False)
async def download_dump(db: AsyncSession = Depends(get_db)):
    """Generate a pg_dump-style SQL export of all data."""
    from fastapi.responses import StreamingResponse
    import io

    tables = [
        ("municipalities", "SELECT id, cbs_code, name FROM municipalities ORDER BY name"),
        ("national_parties", "SELECT id, name FROM national_parties ORDER BY name"),
        ("parties", "SELECT id, municipality_id, national_party_id, raw_name, party_type, is_coalition, kiesraad_list_number FROM parties ORDER BY raw_name"),
        ("party_websites", "SELECT id, party_id, url, status FROM party_websites ORDER BY party_id"),
        ("programs", "SELECT id, party_id, source_url, file_type, raw_text, word_count, qc_method, qc_correct_term, qc_correct_municipality, qc_correct_party, qc_is_program, qc_notes, overall_quality, qc_escalated, not_found FROM programs ORDER BY party_id"),
    ]

    async def generate():
        yield "-- Polok database dump\n-- Generated automatically\n\n"
        for table_name, query in tables:
            result = await db.execute(select(func.count()).select_from(select(Program).subquery()) if table_name == "x" else __import__("sqlalchemy").text(query))
            rows = result.fetchall()
            cols = list(result.keys())
            yield f"-- {table_name}: {len(rows)} rows\n"
            for row in rows:
                vals = []
                for v in row:
                    if v is None:
                        vals.append("NULL")
                    elif isinstance(v, bool):
                        vals.append("TRUE" if v else "FALSE")
                    elif isinstance(v, (int, float)):
                        vals.append(str(v))
                    else:
                        vals.append("'" + str(v).replace("'", "''") + "'")
                yield f"INSERT INTO {table_name} ({','.join(cols)}) VALUES ({','.join(vals)});\n"
            yield "\n"

    return StreamingResponse(
        generate(),
        media_type="application/sql",
        headers={"Content-Disposition": "attachment; filename=polok-dump.sql"},
    )


# --- HTML pages ---

@router.get("/programmas", response_class=HTMLResponse, include_in_schema=False)
async def programs_page(request: Request, db: AsyncSession = Depends(get_db)):
    return templates.TemplateResponse("programs.html", {"request": request})


@router.get("/kaart", response_class=HTMLResponse, include_in_schema=False)
async def map_page(request: Request):
    return templates.TemplateResponse("map.html", {"request": request})
