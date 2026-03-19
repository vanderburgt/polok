"""Party management routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.auth import verify_api_key
from app.models import (
    Municipality,
    NationalParty,
    Party,
    PartyType,
    Program,
    QualityResult,
    WebsiteStatus,
)

router = APIRouter(tags=["partijen"])
templates = Jinja2Templates(directory="app/templates")


async def _query_parties(
    db: AsyncSession,
    gemeente: str | None = None,
    zoek: str | None = None,
    partij_type: str | None = None,
    landelijke_partij: str | None = None,
    heeft_programma: bool | None = None,
    pagina: int = 1,
    per_pagina: int = 50,
):
    query = select(Party).options(
        selectinload(Party.municipality),
        selectinload(Party.national_party),
        selectinload(Party.websites),
        selectinload(Party.programs),
    )

    if gemeente:
        query = query.join(Party.municipality).where(Municipality.name.ilike(f"%{gemeente}%"))
    if zoek:
        if not gemeente:
            query = query.join(Party.municipality, isouter=True)
        query = query.where(Party.raw_name.ilike(f"%{zoek}%"))
    if partij_type:
        query = query.where(Party.party_type == PartyType(partij_type))
    if landelijke_partij == "lokaal":
        query = query.where(Party.national_party_id.is_(None))
    elif landelijke_partij:
        query = query.join(Party.national_party).where(NationalParty.name == landelijke_partij)
    if heeft_programma is True:
        query = query.where(
            Party.id.in_(select(Program.party_id).where(Program.overall_quality == QualityResult.PASS))
        )
    elif heeft_programma is False:
        query = query.where(
            ~Party.id.in_(select(Program.party_id).where(Program.overall_quality == QualityResult.PASS))
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(Party.raw_name).offset((pagina - 1) * per_pagina).limit(per_pagina)
    result = await db.execute(query)
    parties = result.scalars().all()

    return {
        "totaal": total,
        "pagina": pagina,
        "per_pagina": per_pagina,
        "totaal_paginas": (total + per_pagina - 1) // per_pagina,
        "partijen": [
            {
                "id": str(p.id),
                "naam": p.raw_name,
                "partij_type": p.party_type.value,
                "is_coalitie": p.is_coalition,
                "gemeente": p.municipality.name,
                "landelijke_partij": p.national_party.name if p.national_party else None,
                "website": next(
                    (w.url for w in p.websites if w.status == WebsiteStatus.confirmed),
                    None,
                ),
                "heeft_programma": any(
                    pr.overall_quality and pr.overall_quality.value == "pass"
                    for pr in p.programs
                ),
            }
            for p in parties
        ],
    }


async def _query_national_parties(db: AsyncSession):
    result = await db.execute(select(NationalParty).order_by(NationalParty.name))
    return {
        "partijen": [
            {"id": str(p.id), "naam": p.name}
            for p in result.scalars().all()
        ]
    }


# --- Public API (key required) ---

@router.get("/api/partijen", dependencies=[Depends(verify_api_key)])
async def api_list_parties(
    db: AsyncSession = Depends(get_db),
    gemeente: str | None = None, zoek: str | None = None,
    partij_type: str | None = None, landelijke_partij: str | None = None,
    heeft_programma: bool | None = None, pagina: int = 1, per_pagina: int = 50,
):
    """Lijst van partijen met filters."""
    return await _query_parties(db, gemeente, zoek, partij_type, landelijke_partij, heeft_programma, pagina, per_pagina)


@router.get("/api/landelijke-partijen", dependencies=[Depends(verify_api_key)])
async def api_list_national_parties(db: AsyncSession = Depends(get_db)):
    """Lijst van landelijke partijen."""
    return await _query_national_parties(db)


# --- Internal endpoints for web UI (no key) ---

@router.get("/_data/partijen", include_in_schema=False)
async def internal_list_parties(
    db: AsyncSession = Depends(get_db),
    gemeente: str | None = None, zoek: str | None = None,
    partij_type: str | None = None, landelijke_partij: str | None = None,
    heeft_programma: bool | None = None, pagina: int = 1, per_pagina: int = 50,
):
    return await _query_parties(db, gemeente, zoek, partij_type, landelijke_partij, heeft_programma, pagina, per_pagina)


# --- HTML page ---

@router.get("/partijen", response_class=HTMLResponse, include_in_schema=False)
async def parties_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NationalParty).order_by(NationalParty.name))
    national_parties = result.scalars().all()
    return templates.TemplateResponse("parties.html", {
        "request": request,
        "national_parties": national_parties,
    })
