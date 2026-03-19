# Polok Web

Web interface and API for browsing Dutch municipal election programs (verkiezingsprogramma's) from the 2026 gemeenteraadsverkiezingen.

Part of the [Lokale Lobby](https://github.com/openstate) project by [Open State Foundation](https://openstate.eu/) in collaboration with NOS Bureau Regio.

## What's in here

- **Web UI** at `/programmas` and `/partijen` — browse and filter programs and parties
- **REST API** at `/api/` — authenticated JSON API (Swagger docs at `/api/docs`)
- **2,819 programs** from 2,901 parties across 340 Dutch municipalities
- **Quality-checked** — each program has automated QC results (pass/fail/uncertain)

## Quick start

```bash
cp .env.example .env
# Edit .env: set API_KEYS=your-secret-key

docker compose up
```

The app will be available at http://localhost:8002.

## API

All `/api/` endpoints require an `X-API-Key` header. Set `API_KEYS` in your `.env` (comma-separated for multiple keys).

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/programmas` | List programs with filters |
| GET | `/api/programmas/stats` | Aggregate statistics |
| GET | `/api/programmas/{id}/tekst` | Full program text |
| GET | `/api/partijen` | List parties with filters |
| GET | `/api/landelijke-partijen` | List national parties |

### Program filters

| Parameter | Description |
|-----------|-------------|
| `kwaliteit` | `pass`, `fail`, `uncertain` |
| `zoek` | Search party name or municipality |
| `type` | `pdf` or `html` |
| `min_woorden` | Minimum word count |
| `max_woorden` | Maximum word count |
| `pagina` | Page number (default: 1) |
| `per_pagina` | Results per page (default: 50) |

### Party filters

| Parameter | Description |
|-----------|-------------|
| `zoek` | Search by party name |
| `gemeente` | Filter by municipality name |
| `landelijke_partij` | National party name, or `lokaal` for local parties |
| `heeft_programma` | `true` or `false` |

## Data

The database contains election programs collected and quality-checked for the 2026 Dutch municipal elections. Programs were scraped from party websites, converted to text, and verified using automated quality checks.

## Development

```bash
uv sync
cp .env.example .env
# Start a PostgreSQL database, then:
DATABASE_URL=postgresql+asyncpg://polok:polok@localhost:5432/polok uvicorn app.main:app --reload
```

## License

MIT
