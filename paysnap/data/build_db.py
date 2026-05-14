"""
build_db.py
Run this once after any state JSON update.
Usage: python data/build_db.py
"""

import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
STATES_DIR = BASE_DIR / "states"
DB_PATH = BASE_DIR / "labor_law.db"


def build_database():
    print(f"Building database at {DB_PATH}")

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE state_rules (
            state_code TEXT PRIMARY KEY,
            state_name_en TEXT,
            state_name_es TEXT,
            minimum_wage REAL,
            minimum_wage_alt REAL,
            minimum_wage_alt_desc TEXT,
            minimum_wage_statute TEXT,
            tipped_minimum REAL,
            ot_weekly_threshold INTEGER DEFAULT 40,
            ot_daily_threshold INTEGER,
            ot_multiplier REAL DEFAULT 1.5,
            ot_double_threshold INTEGER,
            ot_double_multiplier REAL,
            ot_statute TEXT,
            paystub_required INTEGER DEFAULT 0,
            paystub_statute TEXT,
            last_verified TEXT,
            source_url TEXT,
            rights_summary_es TEXT,
            rights_summary_en TEXT
        )
    """)

    c.execute("""
        CREATE TABLE deduction_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_code TEXT,
            deduction_type TEXT,
            is_allowed INTEGER,
            requires_written_consent INTEGER DEFAULT 0,
            statute TEXT
        )
    """)

    c.execute("""
        CREATE TABLE legal_aid (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            state_code TEXT,
            organization_name TEXT,
            organization_name_en TEXT,
            organization_name_es TEXT,
            phone TEXT,
            phone_note_en TEXT,
            phone_note_es TEXT,
            url TEXT,
            serves_undocumented INTEGER DEFAULT 1,
            coverage TEXT
        )
    """)

    for state_file in STATES_DIR.glob("*.json"):
        with open(state_file, "r", encoding="utf-8") as f:
            d = json.load(f)
        sc = d["state_code"]

        c.execute("""
            INSERT INTO state_rules VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            sc,
            d["state_name_en"],
            d["state_name_es"],
            d["wages"]["minimum_wage"],
            d["wages"].get("minimum_wage_nyc") or d["wages"].get("minimum_wage_chicago"),
            "City minimum" if (
                d["wages"].get("minimum_wage_nyc") or
                d["wages"].get("minimum_wage_chicago")
            ) else None,
            d["wages"].get("minimum_wage_statute"),
            d["wages"].get("tipped_minimum"),
            d["overtime"]["weekly_threshold"],
            d["overtime"].get("daily_threshold"),
            d["overtime"]["multiplier_standard"],
            d["overtime"].get("double_time_threshold"),
            d["overtime"].get("multiplier_double"),
            d["overtime"].get("statute"),
            1 if d["paystub"]["itemized_required"] else 0,
            d["paystub"].get("statute"),
            d.get("last_verified"),
            d.get("source_url"),
            d.get("worker_rights_summary_es"),
            d.get("worker_rights_summary_en"),
        ))

        for dt in d["deductions"].get("allowed_without_consent", []):
            c.execute(
                "INSERT INTO deduction_rules "
                "(state_code,deduction_type,is_allowed,requires_written_consent,statute) "
                "VALUES (?,?,?,?,?)",
                (sc, dt, 1, 0, d["deductions"].get("statute"))
            )

        for dt in d["deductions"].get("allowed_with_written_consent", []):
            c.execute(
                "INSERT INTO deduction_rules "
                "(state_code,deduction_type,is_allowed,requires_written_consent,statute) "
                "VALUES (?,?,?,?,?)",
                (sc, dt, 1, 1, d["deductions"].get("statute"))
            )

        for dt in d["deductions"].get("never_allowed", []):
            c.execute(
                "INSERT INTO deduction_rules "
                "(state_code,deduction_type,is_allowed,requires_written_consent,statute) "
                "VALUES (?,?,?,?,?)",
                (sc, dt, 0, 0, d["deductions"].get("statute"))
            )

        for contact in d.get("legal_aid", []):
            c.execute(
                "INSERT INTO legal_aid "
                "(state_code,organization_name,organization_name_en,"
                "organization_name_es,phone,phone_note_en,phone_note_es,"
                "url,serves_undocumented,coverage) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    sc,
                    contact["name"],
                    contact.get("name_en", contact["name"]),
                    contact.get("name_es", contact["name"]),
                    contact.get("phone"),
                    contact.get("phone_note_en", "Free, bilingual service available"),
                    contact.get("phone_note_es", "Gratis, servicio en español"),
                    contact.get("url"),
                    1 if contact.get("serves_undocumented") else 0,
                    contact.get("coverage")
                )
            )

        print(f"  Loaded: {sc}")

    conn.commit()
    conn.close()
    print(f"Done. Size: {DB_PATH.stat().st_size // 1024} KB")


if __name__ == "__main__":
    build_database()