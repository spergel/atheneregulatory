"""
Build website/data/ from companies/ schedule CSVs and timeseries JSON.

Run after extract_kpis.py and extract_schedules.py.

  python build_web_data.py             # all companies
  python build_web_data.py jackson     # specific company
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
CO_DIR = BASE / "companies"
WEB_DATA = BASE / "website" / "data"

COMPANIES = {
    "athene":      {"name": "Athene",                 "ticker": "ATH",  "entities": ["AAIA"]},
    "brighthouse": {"name": "Brighthouse Financial",  "ticker": "BHF",  "entities": ["BLIC", "NELIC", "BLICNY"]},
    "cno":         {"name": "CNO Financial",          "ticker": "CNO",  "entities": ["BLC", "CPL"]},
    "corebridge":  {"name": "Corebridge Financial",   "ticker": "CRBG", "entities": ["AGL", "VALIC", "USL"]},
    "equitable":   {"name": "Equitable Holdings",     "ticker": "EQH",  "entities": ["EFLIC", "EFLOA"]},
    "jackson":     {"name": "Jackson Financial",      "ticker": "JXN",  "entities": ["JNLIC", "JNLICNY"]},
    "lincoln":     {"name": "Lincoln National",       "ticker": "LNC",  "entities": ["LNL", "LLANY"]},
    "metlife":     {"name": "MetLife",                "ticker": "MET",  "entities": ["MLIC", "MTL"]},
    "principal":   {"name": "Principal Financial",    "ticker": "PFG",  "entities": ["PLIC"]},
    "prudential":  {"name": "Prudential Financial",   "ticker": "PRU",  "entities": ["PICA"]},
    "unum":        {"name": "Unum Group",             "ticker": "UNM",  "entities": ["FUNM", "ULAM"]},
    "voya":        {"name": "Voya Financial",         "ticker": "VOYA", "entities": ["VRIAC"]},
}

CROSSFIRM_FIELDS = [
    "bonds", "mortgages", "alts", "cash", "real_estate",
    "total_invested", "annuity_ytd", "life_prem_ytd",
]

VALID_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM",
    "NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA",
    "WV","WI","WY","PR","VI","GU","MP","AS",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pn(s: str) -> float:
    if not s or not s.strip():
        return 0.0
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.replace("(", "").replace(")", "").replace(",", "").strip()
    try:
        return -float(s) if neg else float(s)
    except ValueError:
        return 0.0


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Schedule parsers
# ---------------------------------------------------------------------------

def parse_sched_t(path: Path) -> list[dict]:
    rows = read_csv(path)
    # Deduplicate per state: keep the row with highest life+annuity total
    # (Schedule T sometimes has both "direct" and aggregate rows per state)
    best: dict[str, dict] = {}
    for r in rows:
        code = r.get("state_code", "").strip()
        if code not in VALID_STATES:
            continue
        life = pn(r.get("life", ""))
        ann  = pn(r.get("annuity", ""))
        if life == 0 and ann == 0:
            continue
        total = life + ann
        if code not in best or total > best[code]["total"]:
            best[code] = {
                "state":   code,
                "name":    r.get("state", "").strip(),
                "life":    life,
                "annuity": ann,
                "total":   total,
            }
    result = sorted(best.values(), key=lambda x: -x["total"])
    return result


def parse_sched_d_quality(path: Path) -> list[dict]:
    rows = read_csv(path)
    result = []
    for r in rows:
        cat   = r.get("category", "").strip()
        desig = r.get("naic_designation", "").strip()
        cur   = pn(r.get("total_current_year", ""))
        prior = pn(r.get("total_prior_year", ""))
        if not desig or cur == 0:
            continue
        result.append({"category": cat, "naic": desig, "current": cur, "prior": prior})
    return result


def parse_sched_b(path: Path) -> dict:
    """Aggregate individual mortgage rows into summaries."""
    rows = read_csv(path)
    by_state: dict = defaultdict(lambda: {"count": 0, "bv": 0.0, "rates": []})
    rate_buckets: dict = defaultdict(int)
    top_loans = []

    for r in rows:
        st   = r.get("state", "").strip()
        bv   = pn(r.get("book_value", ""))
        rate = pn(r.get("interest_rate", ""))

        if st in VALID_STATES:
            by_state[st]["count"] += 1
            by_state[st]["bv"]    += bv
            if rate > 0:
                by_state[st]["rates"].append(rate)

        if 0 < rate <= 20:
            bucket = round(rate * 2) / 2
            rate_buckets[bucket] += 1

        if bv > 0:
            top_loans.append({"city": r.get("city", ""), "state": st, "bv": bv, "rate": rate})

    # Build by_state list with avg_rate
    by_state_list = []
    for st, d in sorted(by_state.items(), key=lambda x: -x[1]["bv"]):
        avg = sum(d["rates"]) / len(d["rates"]) if d["rates"] else 0
        by_state_list.append({"state": st, "count": d["count"], "bv": d["bv"], "avg_rate": round(avg, 3)})

    top_loans.sort(key=lambda x: -x["bv"])
    rate_histogram = [{"rate": k, "count": v} for k, v in sorted(rate_buckets.items())]

    return {
        "count": len(rows),
        "total_bv": sum(r["bv"] for r in by_state_list),
        "by_state": by_state_list,
        "rate_histogram": rate_histogram,
        "top_loans": top_loans[:50],
    }


def parse_sched_ba(path: Path) -> dict:
    rows = read_csv(path)
    total_bv = sum(pn(r.get("book_value", "")) for r in rows)
    items = []
    for r in rows:
        bv = pn(r.get("book_value", ""))
        if bv == 0:
            continue
        items.append({
            "name":  r.get("name", "").strip()[:60],
            "state": r.get("state", "").strip(),
            "bv":    bv,
            "income": pn(r.get("investment_income", "")),
        })
    items.sort(key=lambda x: -x["bv"])
    return {"count": len(rows), "total_bv": total_bv, "top": items[:100]}


# ---------------------------------------------------------------------------
# Per-period detail file: website/data/{co}/{entity}_{period}.json
# ---------------------------------------------------------------------------

def build_period_file(co_key: str, entity: str, period: str, sched_dir: Path, out_dir: Path) -> dict | None:
    stem = f"{entity}_{period}"
    t_path  = sched_dir / f"{stem}_sched_t.csv"
    dq_path = sched_dir / f"{stem}_sched_d_quality.csv"
    b_path  = sched_dir / f"{stem}_sched_b.csv"
    ba_path = sched_dir / f"{stem}_sched_ba.csv"

    if not any(p.exists() for p in [t_path, dq_path, b_path, ba_path]):
        return None

    out: dict = {"entity": entity, "period": period}
    if t_path.exists():
        out["sched_t"] = parse_sched_t(t_path)
    if dq_path.exists():
        out["sched_d_quality"] = parse_sched_d_quality(dq_path)
    if b_path.exists():
        out["sched_b"] = parse_sched_b(b_path)
        _write_sched_b_full(b_path, out_dir / f"{stem}_sched_b.csv")
    if ba_path.exists():
        out["sched_ba"] = parse_sched_ba(ba_path)
        _write_sched_ba_full(ba_path, out_dir / f"{stem}_sched_ba.csv")
    return out


def _write_sched_b_full(src: Path, dest: Path) -> None:
    """Copy Schedule B trimmed to display columns."""
    rows = read_csv(src)
    fields = ["loan_number", "city", "state", "date_acquired", "interest_rate", "book_value"]
    write_csv_file(dest, fields, rows)


def _write_sched_ba_full(src: Path, dest: Path) -> None:
    """Copy Schedule BA trimmed to display columns, sorted by book value desc."""
    rows = read_csv(src)
    rows.sort(key=lambda r: pn(r.get("book_value", "")), reverse=True)
    fields = ["name", "state", "date_acquired", "book_value", "investment_income", "ownership_pct"]
    write_csv_file(dest, fields, rows)


# ---------------------------------------------------------------------------
# Overview file: website/data/{co}/overview.json
# ---------------------------------------------------------------------------

def build_overview(co_key: str, meta: dict) -> dict:
    co_dir    = CO_DIR / co_key
    ts_path   = co_dir / "all_timeseries.json"
    sched_dir = co_dir / "schedules"

    timeseries = []
    if ts_path.exists():
        timeseries = json.loads(ts_path.read_text(encoding="utf-8"))

    # Find available entity+period combos from schedule CSVs
    entity_periods: dict[str, list[str]] = defaultdict(set)
    if sched_dir.exists():
        for f in sched_dir.glob("*_sched_t.csv"):
            parts = f.stem.rsplit("_sched_", 1)[0]
            for entity in meta["entities"]:
                if parts.startswith(entity + "_"):
                    period = parts[len(entity) + 1:]
                    entity_periods[entity].add(period)

    ep_sorted = {e: sorted(p) for e, p in entity_periods.items()}

    # Latest period for primary entity (largest entity = most KPI data)
    latest_data = {}
    primary = meta["entities"][0]
    if ep_sorted.get(primary):
        latest_period = ep_sorted[primary][-1]
        stem = f"{primary}_{latest_period}"
        t_path  = sched_dir / f"{stem}_sched_t.csv"  if sched_dir.exists() else None
        dq_path = sched_dir / f"{stem}_sched_d_quality.csv" if sched_dir.exists() else None
        if t_path and t_path.exists():
            latest_data["sched_t"] = parse_sched_t(t_path)
        if dq_path and dq_path.exists():
            latest_data["sched_d_quality"] = parse_sched_d_quality(dq_path)
        latest_data["period"] = latest_period
        latest_data["entity"] = primary

    return {
        "meta": meta,
        "timeseries": timeseries,
        "entity_periods": ep_sorted,
        "latest": latest_data,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_company(co_key: str):
    meta = COMPANIES[co_key]
    print(f"\n{meta['name']} ({co_key})")

    out_dir = WEB_DATA / co_key
    out_dir.mkdir(parents=True, exist_ok=True)

    # Overview
    overview = build_overview(co_key, meta)
    (out_dir / "overview.json").write_text(json.dumps(overview, separators=(",", ":")), encoding="utf-8")

    ep = overview["entity_periods"]
    ep_count = sum(len(v) for v in ep.values())
    print(f"  overview.json: {len(overview['timeseries'])} timeseries rows, {ep_count} entity-periods")

    # Per-period detail files
    sched_dir = CO_DIR / co_key / "schedules"
    built = 0
    for entity, periods in ep.items():
        for period in periods:
            data = build_period_file(co_key, entity, period, sched_dir, out_dir)
            if data:
                fname = f"{entity}_{period}.json"
                (out_dir / fname).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
                built += 1
    print(f"  Period files: {built}")


def build_crossfirm() -> None:
    """Generate website/data/crossfirm.json with aggregated per-company timeseries."""
    print("\nBuilding cross-firm data...")
    companies_out = {}

    for co_key, meta in COMPANIES.items():
        ts_path = CO_DIR / co_key / "all_timeseries.json"
        if not ts_path.exists():
            continue
        ts = json.loads(ts_path.read_text(encoding="utf-8"))

        # Sum all entities per period to get company-level totals
        by_period: dict = defaultdict(lambda: {f: 0.0 for f in CROSSFIRM_FIELDS})
        for row in ts:
            p = row["period"]
            for field in CROSSFIRM_FIELDS:
                by_period[p][field] += row.get(field, 0.0)

        sorted_periods = sorted(by_period.keys())
        companies_out[co_key] = {
            "name":    meta["name"],
            "ticker":  meta["ticker"],
            "periods": sorted_periods,
            "timeseries": [{"period": p, **by_period[p]} for p in sorted_periods],
        }
        print(f"  {co_key}: {len(sorted_periods)} periods")

    (WEB_DATA / "crossfirm.json").write_text(
        json.dumps(companies_out, separators=(",", ":")), encoding="utf-8"
    )
    size_kb = (WEB_DATA / "crossfirm.json").stat().st_size // 1024
    print(f"  crossfirm.json ({size_kb} KB)")


def write_csv_file(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def build_company_csvs(co_key: str, meta: dict) -> None:
    """Generate per-company combined CSVs from raw schedule CSVs."""
    sched_dir = CO_DIR / co_key / "schedules"
    out_dir   = WEB_DATA / co_key
    if not sched_dir.exists():
        return

    # --- Schedule T (all periods) ---
    t_rows: list[dict] = []
    for f in sorted(sched_dir.glob("*_sched_t.csv")):
        stem = f.stem.replace("_sched_t", "")
        entity, period = _split_stem(stem, meta["entities"])
        for r in read_csv(f):
            t_rows.append({"entity": entity, "period": period, **r})
    if t_rows:
        write_csv_file(out_dir / "sched_t_all.csv",
            ["entity","period","state","state_code","life","annuity","ah","other","total","deposit"],
            t_rows)

    # --- Schedule D Quality (annual filings) ---
    dq_rows: list[dict] = []
    for f in sorted(sched_dir.glob("*_sched_d_quality.csv")):
        stem = f.stem.replace("_sched_d_quality", "")
        entity, period = _split_stem(stem, meta["entities"])
        for r in read_csv(f):
            dq_rows.append({"entity": entity, "period": period, **r})
    if dq_rows:
        write_csv_file(out_dir / "sched_dq_all.csv",
            ["entity","period","category","naic_designation","total_current_year","total_prior_year"],
            dq_rows)

    # --- Schedule B — state-level summary (not individual loans) ---
    b_rows: list[dict] = []
    for f in sorted(sched_dir.glob("*_sched_b.csv")):
        stem = f.stem.replace("_sched_b", "")
        entity, period = _split_stem(stem, meta["entities"])
        by_state: dict = defaultdict(lambda: {"count": 0, "total_bv": 0.0, "rates": []})
        for r in read_csv(f):
            st = r.get("state", "").strip()
            bv = pn(r.get("book_value", ""))
            rate = pn(r.get("interest_rate", ""))
            if st:
                by_state[st]["count"] += 1
                by_state[st]["total_bv"] += bv
                if 0 < rate <= 20:
                    by_state[st]["rates"].append(rate)
        for st, d in sorted(by_state.items()):
            avg = sum(d["rates"]) / len(d["rates"]) if d["rates"] else 0
            b_rows.append({
                "entity": entity, "period": period, "state": st,
                "loan_count": d["count"], "total_book_value": round(d["total_bv"], 2),
                "avg_interest_rate": round(avg, 4),
            })
    if b_rows:
        write_csv_file(out_dir / "sched_b_states.csv",
            ["entity","period","state","loan_count","total_book_value","avg_interest_rate"],
            b_rows)

    # --- Schedule BA — top holdings per period ---
    ba_rows: list[dict] = []
    for f in sorted(sched_dir.glob("*_sched_ba.csv")):
        stem = f.stem.replace("_sched_ba", "")
        entity, period = _split_stem(stem, meta["entities"])
        items = []
        for r in read_csv(f):
            bv = pn(r.get("book_value", ""))
            items.append({"entity": entity, "period": period,
                          "name": r.get("name","")[:80], "state": r.get("state",""),
                          "date_acquired": r.get("date_acquired",""),
                          "book_value": bv,
                          "investment_income": r.get("investment_income",""),
                          "ownership_pct": r.get("ownership_pct","")})
        items.sort(key=lambda x: -x["book_value"])
        ba_rows.extend(items[:500])  # top 500 per period
    if ba_rows:
        write_csv_file(out_dir / "sched_ba_all.csv",
            ["entity","period","name","state","date_acquired","book_value","investment_income","ownership_pct"],
            ba_rows)


def _split_stem(stem: str, entities: list[str]) -> tuple[str, str]:
    """Split 'JNLIC_2024Q4' into ('JNLIC', '2024Q4') using known entity list."""
    for e in entities:
        if stem.startswith(e + "_"):
            return e, stem[len(e)+1:]
    # Fallback: assume last token is period
    parts = stem.rsplit("_", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (stem, "")


def build_flat_downloads() -> None:
    """Generate flat CSVs combining all companies for easy download."""
    print("\nBuilding flat download CSVs...")

    # All timeseries
    all_ts_rows = []
    for co_key, meta in COMPANIES.items():
        ts_path = CO_DIR / co_key / "all_timeseries.json"
        if not ts_path.exists():
            continue
        for row in json.loads(ts_path.read_text(encoding="utf-8")):
            all_ts_rows.append({"company": meta["name"], "ticker": meta["ticker"], **row})

    if all_ts_rows:
        fields = ["company","ticker","entity","period",
                  "bonds","mortgages","alts","cash","real_estate",
                  "total_invested","annuity_ytd","life_prem_ytd"]
        out = WEB_DATA / "download_all_timeseries.csv"
        write_csv_file(out, fields, all_ts_rows)
        print(f"  download_all_timeseries.csv ({len(all_ts_rows)} rows)")

    # Per-company combined CSVs
    for co_key, meta in COMPANIES.items():
        build_company_csvs(co_key, meta)
    print("  Per-company schedule CSVs built")

    # Catalog JSON
    catalog: list[dict] = []
    for co_key, meta in COMPANIES.items():
        co_dir = WEB_DATA / co_key
        if not co_dir.exists():
            continue
        for f in sorted(co_dir.glob("*.json")):
            if f.name == "overview.json":
                continue
            data = json.loads(f.read_text(encoding="utf-8"))
            catalog.append({
                "company":     co_key,
                "name":        meta["name"],
                "ticker":      meta["ticker"],
                "entity":      data.get("entity", ""),
                "period":      data.get("period", ""),
                "size_kb":     f.stat().st_size // 1024,
                "has_sched_t":  "sched_t" in data,
                "has_sched_b":  "sched_b" in data,
                "has_sched_ba": "sched_ba" in data,
                "has_sched_dq": "sched_d_quality" in data,
            })
    (WEB_DATA / "catalog.json").write_text(
        json.dumps(catalog, separators=(",", ":")), encoding="utf-8")
    print(f"  catalog.json ({len(catalog)} entries)")


def main():
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(COMPANIES.keys())
    full_build = not sys.argv[1:]  # only build cross-firm on full rebuild
    unknown = [t for t in targets if t not in COMPANIES]
    if unknown:
        print(f"Unknown: {unknown}. Available: {sorted(COMPANIES.keys())}")
        return

    WEB_DATA.mkdir(parents=True, exist_ok=True)

    # companies.json index
    index = {k: {"name": v["name"], "ticker": v["ticker"], "entities": v["entities"]}
             for k, v in COMPANIES.items()}
    (WEB_DATA / "companies.json").write_text(json.dumps(index, indent=2), encoding="utf-8")

    for co_key in targets:
        build_company(co_key)

    if full_build:
        build_crossfirm()
        build_flat_downloads()

    print("\nDone.")


if __name__ == "__main__":
    main()
