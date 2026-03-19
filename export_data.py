"""Export database tables to CSV files in data/ for committing to the repo.

Usage:
    DATABASE_URL=postgresql+psycopg://polok:polok@localhost:5432/polok python export_data.py
"""
import csv
import gzip
import os
import sys

import psycopg

DB_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://polok:polok@localhost:5432/polok")
# Normalize for psycopg
DB_URL = DB_URL.replace("+asyncpg", "+psycopg").replace("+psycopg", "")
if DB_URL.startswith("postgresql://"):
    pass
elif "://" not in DB_URL:
    DB_URL = "postgresql://" + DB_URL

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

TABLES = {
    "municipalities": "SELECT id, cbs_code, name FROM municipalities ORDER BY name",
    "national_parties": "SELECT id, name FROM national_parties ORDER BY name",
    "parties": """
        SELECT id, municipality_id, national_party_id, raw_name, party_type,
               is_coalition, kiesraad_list_number
        FROM parties ORDER BY raw_name
    """,
    "party_websites": """
        SELECT id, party_id, url, status
        FROM party_websites ORDER BY party_id
    """,
    "programs_meta": """
        SELECT id, party_id, source_url, file_type, word_count,
               qc_method, qc_correct_term, qc_correct_municipality,
               qc_correct_party, qc_is_program, qc_notes, overall_quality,
               qc_escalated, not_found
        FROM programs ORDER BY party_id
    """,
}


def export_table(conn, name, query, path):
    """Export a query result to CSV."""
    cur = conn.execute(query)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    print(f"  {name}: {len(rows)} rows -> {path}")


def export_texts(conn):
    """Export program texts to a gzipped CSV."""
    path = os.path.join(DATA_DIR, "programs_text.csv.gz")
    cur = conn.execute(
        "SELECT id, raw_text FROM programs WHERE raw_text IS NOT NULL ORDER BY id"
    )
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    with gzip.open(path, "wt", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    size_mb = os.path.getsize(path) / 1024 / 1024
    print(f"  programs_text: {len(rows)} rows -> {path} ({size_mb:.1f} MB)")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"Connecting to {DB_URL.split('@')[-1]}...")

    with psycopg.connect(DB_URL) as conn:
        for name, query in TABLES.items():
            path = os.path.join(DATA_DIR, f"{name}.csv")
            export_table(conn, name, query, path)

        export_texts(conn)

    print("Done.")


if __name__ == "__main__":
    main()
