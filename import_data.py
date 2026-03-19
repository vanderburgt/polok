"""Import CSV data from data/ into the database.

Designed to run on startup: skips import if data already exists.
Can be forced with --force flag to wipe and reimport.

Usage:
    DATABASE_URL=postgresql+psycopg://polok:polok@localhost:5432/polok python import_data.py [--force]
"""
import csv
import gzip
import io
import os
import sys

csv.field_size_limit(sys.maxsize)

import psycopg

DB_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://polok:polok@localhost:5432/polok")
DB_URL = DB_URL.replace("+asyncpg", "+psycopg").replace("+psycopg", "")
if DB_URL.startswith("postgresql://"):
    pass
elif "://" not in DB_URL:
    DB_URL = "postgresql://" + DB_URL

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Import order respects foreign keys
TABLES = [
    ("municipalities", "municipalities.csv", ["id", "cbs_code", "name"]),
    ("national_parties", "national_parties.csv", ["id", "name"]),
    ("parties", "parties.csv", [
        "id", "municipality_id", "national_party_id", "raw_name",
        "party_type", "is_coalition", "kiesraad_list_number",
    ]),
    ("party_websites", "party_websites.csv", ["id", "party_id", "url", "status"]),
    ("programs", "programs_meta.csv", [
        "id", "party_id", "source_url", "file_type", "word_count",
        "qc_method", "qc_correct_term", "qc_correct_municipality",
        "qc_correct_party", "qc_is_program", "qc_notes", "overall_quality",
        "qc_escalated", "not_found",
    ]),
]

# Columns that are boolean
BOOL_COLS = {
    "is_coalition", "qc_correct_term", "qc_correct_municipality",
    "qc_correct_party", "qc_is_program", "qc_escalated", "not_found",
}


def convert_value(col, val):
    """Convert CSV string values to appropriate Python types."""
    if val == "" or val is None:
        return None
    if col in BOOL_COLS:
        return val.lower() in ("true", "t", "1", "yes")
    if col == "word_count" or col == "kiesraad_list_number":
        return int(val) if val else None
    return val


def has_data(conn):
    """Check if the database already has data."""
    row = conn.execute("SELECT COUNT(*) FROM municipalities").fetchone()
    return row[0] > 0


def import_table(conn, table, filename, columns):
    """Import a CSV file into a table using COPY for speed."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"  {table}: SKIPPED (file not found: {filename})")
        return

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            rows.append(tuple(convert_value(col, row.get(col)) for col in columns))

    if not rows:
        print(f"  {table}: SKIPPED (no data)")
        return

    placeholders = ", ".join(["%s"] * len(columns))
    col_names = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"

    with conn.cursor() as cur:
        cur.executemany(sql, rows)

    print(f"  {table}: {len(rows)} rows imported")


def import_texts(conn):
    """Import program texts from gzipped CSV."""
    path = os.path.join(DATA_DIR, "programs_text.csv.gz")
    if not os.path.exists(path):
        print("  programs_text: SKIPPED (file not found)")
        return

    count = 0
    with gzip.open(path, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        with conn.cursor() as cur:
            for row in reader:
                cur.execute(
                    "UPDATE programs SET raw_text = %s WHERE id = %s",
                    (row["raw_text"], row["id"]),
                )
                count += 1

    print(f"  programs_text: {count} texts imported")


def ensure_schema(conn):
    """Run alembic migrations to ensure schema exists."""
    row = conn.execute(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'municipalities')"
    ).fetchone()
    if row[0]:
        return

    print("Schema not found, running alembic migrations...")
    import subprocess
    env = os.environ.copy()
    env["DATABASE_URL"] = DB_URL
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=os.path.dirname(__file__),
        env=env,
        check=True,
    )
    print("Migrations complete.")


def main():
    force = "--force" in sys.argv

    print(f"Connecting to {DB_URL.split('@')[-1]}...")

    with psycopg.connect(DB_URL, autocommit=False) as conn:
        ensure_schema(conn)

        if not force and has_data(conn):
            print("Database already has data. Use --force to reimport.")
            return

        print("Clearing tables before import...")
        conn.execute("TRUNCATE programs, party_websites, parties, national_parties, municipalities CASCADE")
        conn.commit()

        print("Importing data...")
        for table, filename, columns in TABLES:
            import_table(conn, table, filename, columns)

        import_texts(conn)

        conn.commit()
        print("Done.")


if __name__ == "__main__":
    main()
