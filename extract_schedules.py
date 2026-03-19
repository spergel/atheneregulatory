"""
Extract schedule-level data from all statutory filing text files.

For each company/entity/period, runs schedule parsers and writes:
  companies/{co}/schedules/{ENTITY}_{PERIOD}_sched_t.csv
  companies/{co}/schedules/{ENTITY}_{PERIOD}_sched_b.csv
  companies/{co}/schedules/{ENTITY}_{PERIOD}_sched_ba.csv
  companies/{co}/schedules/{ENTITY}_{PERIOD}_sched_d_quality.csv

Run:
  python extract_schedules.py [company ...]
  python extract_schedules.py              # all companies
"""

import csv
import sys
from pathlib import Path

from lib.schedule_parsers import (
    parse_schedule_b,
    parse_schedule_ba,
    parse_schedule_d_quality,
    parse_schedule_t,
)

BASE = Path(__file__).resolve().parent
COMPANIES_DIR = BASE / "companies"

PARSERS = [
    ("sched_t",         parse_schedule_t,         ["state", "state_code", "life", "annuity", "ah", "other", "total", "deposit"]),
    ("sched_b",         parse_schedule_b,         ["loan_number", "city", "state", "date_acquired", "interest_rate", "book_value", "land_value", "appraisal_date"]),
    ("sched_ba",        parse_schedule_ba,        ["name", "state", "date_acquired", "actual_cost", "fair_value", "book_value", "investment_income", "ownership_pct"]),
    ("sched_d_quality", parse_schedule_d_quality, ["category", "naic_designation", "total_current_year", "total_prior_year"]),
]


def process_file(txt_path: Path, sched_dir: Path) -> dict[str, int]:
    """Parse all schedules from one extracted text file. Returns row counts."""
    text = txt_path.read_text(encoding="utf-8", errors="ignore")
    stem = txt_path.stem  # e.g. "AGL_2024Q4"
    counts = {}

    for sched_name, parser_fn, fields in PARSERS:
        out_path = sched_dir / f"{stem}_{sched_name}.csv"
        if out_path.exists():
            counts[sched_name] = -1  # skip
            continue

        rows = parser_fn(text)
        if not rows:
            counts[sched_name] = 0
            continue

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        counts[sched_name] = len(rows)

    return counts


def process_company(company_dir: Path) -> None:
    extracted_dir = company_dir / "extracted"
    sched_dir = company_dir / "schedules"

    txt_files = sorted(extracted_dir.glob("*.txt"))
    if not txt_files:
        return

    sched_dir.mkdir(exist_ok=True)
    company = company_dir.name
    print(f"\n-- {company.upper()} ({len(txt_files)} files) --")

    for txt_path in txt_files:
        counts = process_file(txt_path, sched_dir)
        parts = []
        for name, n in counts.items():
            if n == -1:
                parts.append(f"{name}=[skip]")
            elif n == 0:
                parts.append(f"{name}=none")
            else:
                parts.append(f"{name}={n}")
        print(f"  {txt_path.stem}: {', '.join(parts)}")


def main():
    target_companies = sys.argv[1:] if len(sys.argv) > 1 else None

    company_dirs = sorted(
        d for d in COMPANIES_DIR.iterdir()
        if d.is_dir() and (target_companies is None or d.name in target_companies)
    )

    if not company_dirs:
        print(f"No company directories found in {COMPANIES_DIR}")
        return

    print(f"Extracting schedules from {len(company_dirs)} companies...")
    for co_dir in company_dirs:
        process_company(co_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()
