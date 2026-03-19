"""
Extract time-series KPIs from all statutory filing text files.

Covers all companies in companies/.
Outputs per-entity and combined timeseries JSON/CSV to each company dir.

Run:
  python extract_kpis.py [company ...]
  python extract_kpis.py              # all companies
"""

import sys
from pathlib import Path

from lib.kpi_extractor import process_company

BASE = Path(__file__).resolve().parent
COMPANIES_DIR = BASE / "companies"

# company_dir_name -> (display_name, [entities])
COMPANIES: dict[str, tuple[str, list[str]]] = {
    "athene":      ("Athene",                 ["AAIA"]),
    "brighthouse": ("Brighthouse Financial",  ["BLIC", "NELIC", "BLICNY"]),
    "cno":         ("CNO Financial",          ["BLC", "CPL"]),
    "corebridge":  ("Corebridge Financial",   ["AGL", "VALIC", "USL"]),
    "equitable":   ("Equitable Holdings",     ["EFLIC", "EFLOA"]),
    "jackson":     ("Jackson Financial",      ["JNLIC", "JNLICNY"]),
    "lincoln":     ("Lincoln National",       ["LNL", "LLANY"]),
    "metlife":     ("MetLife",                ["MLIC", "MTL"]),
    "principal":   ("Principal Financial",    ["PLIC"]),
    "prudential":  ("Prudential Financial",   ["PICA"]),
    "unum":        ("Unum Group",             ["FUNM", "ULAM"]),
    "voya":        ("Voya Financial",         ["VRIAC"]),
}


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(COMPANIES.keys())
    unknown = [t for t in targets if t not in COMPANIES]
    if unknown:
        print(f"Unknown companies: {unknown}")
        print(f"Available: {sorted(COMPANIES.keys())}")
        return

    print(f"Extracting KPIs for: {', '.join(targets)}\n")
    for key in targets:
        name, entities = COMPANIES[key]
        co_dir = COMPANIES_DIR / key
        txt_dir = co_dir / "extracted"
        if not txt_dir.exists():
            print(f"  {name}: no extracted/ directory — run download first")
            continue
        process_company(name, txt_dir, co_dir, entities)

    print("\nAll done.")


if __name__ == "__main__":
    main()
