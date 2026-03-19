"""
Shared KPI extraction logic for NAIC statutory text files.

Extracts summary-level KPIs from Schedule verification pages and Schedule T.
Used by extract_kpis.py (all companies) and extract_historical_kpis.py (Athene).
"""

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from statistics import median

NUMBER_RE = re.compile(r"\(?\d[\d,]*(?:\.\d+)?\)?")

VALID_STATE_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL",
    "GA","HI","ID","IL","IN","IA","KS","KY","LA","ME",
    "MD","MA","MI","MN","MS","MO","MT","NE","NV","NH",
    "NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI",
    "SC","SD","TN","TX","UT","VT","VA","WA","WV","WI",
    "WY","PR","VI","GU","MP","AS",
}

# Hardcoded overrides for filings with garbled font encoding (EagleTM font +
# no ToUnicode CMap) that pdftotext cannot decode.  Values read directly from
# PDF rendered images.  Applied only when the parser extracts 0 for that field.
# Key: (entity, period)  Value: dict of field -> value
_OVERRIDES: dict[tuple[str, str], dict] = {
    ("BLC",    "2021Q1"): {"bonds": 14_072_414_472, "mortgages": 919_335_169},
    ("BLICNY", "2022Q1"): {"bonds":  1_659_457_662, "mortgages": 267_642_825},
    ("NELIC",  "2022Q1"): {"bonds":    984_840_203, "mortgages":  61_962_175},
}

HEADER = [
    "period", "entity",
    "bonds", "mortgages", "alts", "cash", "real_estate",
    "total_invested", "annuity_ytd", "life_prem_ytd",
]

QUALITY_HEADER = [
    "company", "entity", "period", "metric", "severity", "issue",
    "current_value", "prev_value", "next_value", "q4_median", "ratio",
]

_SCHED_T_ROW = re.compile(
    r"^\s*\d+\.\s+.+?"
    r"\s*\.{5,}\s*"
    r"([A-Z]{2,3})"
    r"\s*\.+\s*[A-Z]+"
    r"\s*\.+\s*"
    r"(.+)$"
)


def parse_num(s: str) -> float:
    if not s or not s.strip():
        return 0.0
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.replace("(", "").replace(")", "").replace(",", "").strip()
    try:
        return -float(s) if neg else float(s)
    except ValueError:
        return 0.0


def extract_verification(text: str, schedule_header: str) -> dict[str, dict]:
    idx = text.find(schedule_header)
    if idx == -1:
        return {}
    search_from = idx + len(schedule_header) + 200
    next_sched = text.find("SCHEDULE ", search_from)
    end = next_sched if (next_sched != -1 and next_sched - idx < 40000) else idx + 15000
    block = text[idx:end]
    result = {}
    for line in block.splitlines():
        m = re.match(r"^\s*(\d+)\.\s+(.+)$", line)
        if not m:
            continue
        lid = m.group(1)
        tail = m.group(2)
        nums = NUMBER_RE.findall(tail)
        nums = [n for n in nums if any(c.isdigit() for c in n) and
                ("," in n or len(n.replace("(", "").replace(")", "")) >= 5)]
        if len(nums) >= 2:
            result[lid] = {"ytd": parse_num(nums[0]), "prior": parse_num(nums[1])}
        elif len(nums) == 1:
            result[lid] = {"ytd": parse_num(nums[0]), "prior": 0.0}
    return result


def _scan_continuation_total(text: str, schedule_header: str) -> float:
    """Fallback for old two-column NAIC format where lines 11-13 carry no totals.

    In some pre-2023 filings the actual statement total appears on unlabeled
    continuation rows after the last numbered line.  The rows are ordered
    smallest-to-largest (stocks sub-total first, then bonds sub-total), so the
    first value >= $1B is the bonds (or bonds+stocks) portfolio total.

    Returns the first value >= $1B found on any unlabeled continuation row,
    or 0.0 if none is found.
    """
    idx = text.find(schedule_header)
    if idx == -1:
        return 0.0
    search_from = idx + len(schedule_header) + 200
    next_sched = text.find("SCHEDULE ", search_from)
    end = next_sched if (next_sched != -1 and next_sched - idx < 40000) else idx + 15000
    block = text[idx:end]

    lines = block.splitlines()
    last_numbered = -1
    for i, line in enumerate(lines):
        if re.match(r"^\s*\d+\.", line):
            last_numbered = i

    if last_numbered == -1:
        return 0.0

    for line in lines[last_numbered + 1:]:
        stripped = line.strip()
        if not stripped or re.match(r"^\s*\d+\.", line):
            continue
        nums = NUMBER_RE.findall(stripped)
        vals = [parse_num(n) for n in nums if any(c.isdigit() for c in n)]
        large = [v for v in vals if v >= 1e9]
        if large:
            return large[0]

    return 0.0


def _scan_schedule_b_repeated(text: str) -> float:
    """Fallback for old-format Schedule B filings where lines 11-15 are blank.

    Two layouts seen in pre-2022 filings:
      A) Old two-column (BLC style): the ending balance appears on labeled lines
         6-10 — the same dollar amount repeated 2-3 times due to column alignment.
      B) BETWEEN YEARS wide format (LNL 2019-2020 style): the ending balance
         appears on unlabeled continuation rows between lines 4-5, again repeated.

    Strategy: collect all numbers >= $100M from EVERY line (labeled or not) in the
    Schedule B section and return the value that appears 2 or more times.  This
    works for both layouts since the ending balance always repeats and other values
    generally appear only once.  To avoid picking up the prior-year balance (line 1),
    we skip the first 5 lines of the block (the header rows).
    """
    idx = text.find("SCHEDULE B - VERIFICATION")
    if idx == -1:
        return 0.0
    search_from = idx + len("SCHEDULE B - VERIFICATION") + 100
    next_sched = text.find("SCHEDULE ", search_from)
    end = next_sched if (next_sched != -1 and next_sched - idx < 20000) else idx + 8000
    block = text[idx:end]

    counts: Counter = Counter()
    lines = block.splitlines()
    # Skip the first ~8 lines (header + line 1 prior-year value) to avoid
    # falsely treating the prior-year balance as the repeated ending balance.
    for line in lines[8:]:
        # Stop at next labeled line-1 to avoid bleed into next schedule
        if re.match(r"^\s*1\.\s+Book", line):
            break
        for n in NUMBER_RE.findall(line):
            if not any(c.isdigit() for c in n):
                continue
            v = parse_num(n)
            if v >= 1e8:  # >= $100M to avoid small incidental values
                counts[v] += 1

    repeated = {v: c for v, c in counts.items() if c >= 2}
    if repeated:
        return max(repeated)
    return 0.0


_TOTAL_BONDS_RE = re.compile(r"13\.\s+Total\s+Bonds", re.IGNORECASE)


def _extract_d_summary_bonds(text: str) -> float:
    """Last-resort fallback: read 'Total Bonds' from SCHEDULE D - SUMMARY BY COUNTRY.

    Annual 'BETWEEN YEARS' format filings (e.g. pre-2022 Lincoln, Voya, Corebridge)
    leave lines 11-13 of the verification table blank.  The authoritative
    Book/Adjusted Carrying Value lives on line 13 ('13. Total Bonds') of the
    SUMMARY BY COUNTRY section that follows.

    Returns the first value >= $1B on that line, or 0.0 if not found.
    """
    idx = text.find("SCHEDULE D - SUMMARY BY COUNTRY")
    if idx == -1:
        return 0.0
    block = text[idx: idx + 12000]
    for line in block.splitlines():
        if not _TOTAL_BONDS_RE.search(line):
            continue
        nums = NUMBER_RE.findall(line)
        nums = [n for n in nums if any(c.isdigit() for c in n) and
                ("," in n or len(n.replace("(", "").replace(")", "")) >= 5)]
        vals = [parse_num(n) for n in nums]
        large = [v for v in vals if v >= 1e9]
        if large:
            return large[0]
    return 0.0


def _extract_assets_page_bonds(text: str) -> float:
    """Last-resort fallback: read bonds from the ASSETS balance-sheet page.

    Abbreviated NAIC filings omit full schedule verification tables but always
    include the ASSETS page.  Two layouts exist:

      A) Quarterly:  '1. Bonds   {value}' — value is inline on the label row.
         Reading the number directly gives the current-period Net Admitted value.

      B) Annual abbreviated:  '1. Bonds (Schedule D)' with no inline value.
         The current-period bonds value appears as a continuation row either
         before or after the label line.  In this layout the first number >= $1B
         anywhere in the ASSETS block is the bonds total (prior-year values are
         also large but appear in different positions; in practice the first
         large number encountered IS the current-year bonds for every observed
         annual abbreviated format).

    Returns 0.0 if no suitable value is found.
    """
    idx = text.find("ASSETS")
    if idx == -1:
        return 0.0
    block = text[idx: idx + 3000]
    lines = block.splitlines()

    def _first_large(source_lines: list[str]) -> float:
        for ln in source_lines:
            s = ln.strip()
            if not s:
                continue
            for n in NUMBER_RE.findall(s):
                if any(c.isdigit() for c in n) and (
                    "," in n or len(n.replace("(", "").replace(")", "")) >= 8
                ):
                    v = parse_num(n)
                    if v >= 1e9:
                        return v
        return 0.0

    for i, line in enumerate(lines):
        if not re.match(r"^\s*1\.\s+Bonds\b", line, re.IGNORECASE):
            continue
        # Layout A: value is on this line
        v = _first_large([line])
        if v:
            return v
        # Layout B: no inline value — scan the whole block
        return _first_large(lines)

    return 0.0


def ending_bv(lines: dict, preferred_ids: list[str]) -> float:
    """Return the largest positive ytd value across all candidate line IDs.

    Most filings put the statement value on line 13 (bonds) or 15 (mortgages).
    Older STAT Summary formats (pre-2023 Prudential, pre-2022 Jackson, etc.)
    place the real portfolio total on line 12, with a tiny residual on line 13.
    Taking the maximum positive value correctly handles both layouts.
    """
    best = 0.0
    for lid in preferred_ids:
        if lid in lines:
            v = lines[lid]["ytd"]
            if v > best:
                best = v
    return best


def extract_schedule_t(text: str) -> tuple[float, float]:
    """Return (annuity_ytd, life_prem_ytd) from Schedule T."""
    idx = text.find("SCHEDULE T")
    if idx == -1:
        return 0.0, 0.0
    block = text[idx: idx + 30000]
    started = False
    annuity = 0.0
    life = 0.0
    for line in block.splitlines():
        if not started:
            if "States, Etc." in line or "STATES, ETC" in line.upper():
                started = True
            continue
        if "DETAILS OF WRITE-INS" in line.upper():
            break
        m = _SCHED_T_ROW.match(line)
        if not m:
            continue
        code = m.group(1).upper()
        if code not in VALID_STATE_CODES:
            continue
        nums = NUMBER_RE.findall(m.group(2))
        nums = [parse_num(n) for n in nums if any(c.isdigit() for c in n)]
        if len(nums) >= 2:
            life += nums[0]
            annuity += nums[1]
    return annuity, life


def extract_period(txt_path: Path, entity: str) -> dict[str, Any]:
    """Extract all KPIs from a single text file."""
    period = txt_path.stem.replace(f"{entity}_", "")
    text = txt_path.read_text(encoding="utf-8", errors="ignore")

    result: dict[str, Any] = {"period": period, "entity": entity}

    d_lines  = extract_verification(text, "SCHEDULE D - VERIFICATION")
    b_lines  = extract_verification(text, "SCHEDULE B - VERIFICATION")
    ba_lines = extract_verification(text, "SCHEDULE BA - VERIFICATION")
    e_lines  = extract_verification(text, "SCHEDULE E - PART 2 - VERIFICATION")
    if not e_lines:
        e_lines = extract_verification(text, "SCHEDULE E - VERIFICATION")
    a_lines  = extract_verification(text, "SCHEDULE A - VERIFICATION")

    bonds_bv = max(ending_bv(d_lines,  ["13", "11", "12", "10"]),
                   _scan_continuation_total(text, "SCHEDULE D - VERIFICATION"))
    summary_bv = 0.0 if bonds_bv else _extract_d_summary_bonds(text)
    assets_bv  = 0.0 if (bonds_bv or summary_bv) else _extract_assets_page_bonds(text)
    result["bonds"] = bonds_bv or summary_bv or assets_bv

    result["mortgages"]   = max(ending_bv(b_lines,  ["13", "15", "14", "11", "12"]),
                                _scan_continuation_total(text, "SCHEDULE B - VERIFICATION"),
                                _scan_schedule_b_repeated(text))
    result["alts"]        = ending_bv(ba_lines, ["13", "11", "12"])
    result["cash"]        = ending_bv(e_lines,  ["12", "10", "11", "13"])
    result["real_estate"] = ending_bv(a_lines,  ["11", "9", "10", "13"])

    result["annuity_ytd"], result["life_prem_ytd"] = extract_schedule_t(text)

    # Apply hardcoded overrides for garbled-font filings (only fills 0 fields)
    for field, value in _OVERRIDES.get((entity, period), {}).items():
        if result.get(field, 0) == 0:
            result[field] = value

    result["total_invested"] = (
        result["bonds"] + result["mortgages"] + result["alts"] +
        result["cash"]  + result["real_estate"]
    )

    return result


def write_timeseries(records: list[dict], out_dir: Path, stem: str) -> None:
    """Write a list of KPI records to JSON and CSV."""
    json_out = out_dir / f"{stem}_timeseries.json"
    json_out.write_text(json.dumps(records, indent=2), encoding="utf-8")

    csv_out = out_dir / f"{stem}_timeseries.csv"
    with csv_out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in HEADER})


def _period_key(period: str) -> tuple[int, int]:
    m = re.match(r"^(\d{4})Q([1-4])$", period or "")
    if not m:
        return (0, 0)
    return (int(m.group(1)), int(m.group(2)))


def detect_quality_flags(company_name: str, records: list[dict]) -> list[dict[str, Any]]:
    """Detect suspicious KPI points for frontend warning badges.

    We flag only clearly suspicious portfolio issues:
    - zero value after a large prior quarter
    - zero value between two non-zero quarters
    - large quarter-over-quarter collapse
    """
    core_metrics = ["total_invested", "bonds", "mortgages"]
    flags: list[dict[str, Any]] = []

    by_entity: dict[str, list[dict]] = {}
    for r in records:
        by_entity.setdefault(r["entity"], []).append(r)

    for entity, rows in by_entity.items():
        rows.sort(key=lambda r: _period_key(r["period"]))

        # Median Q4 values used as entity baseline.
        q4_medians: dict[str, float] = {}
        for metric in core_metrics:
            q4_vals = [float(r.get(metric, 0.0)) for r in rows if r["period"].endswith("Q4") and float(r.get(metric, 0.0)) > 0]
            q4_medians[metric] = median(q4_vals) if q4_vals else 0.0

        for i, row in enumerate(rows):
            period = row["period"]
            for metric in core_metrics:
                cur = float(row.get(metric, 0.0))
                prev = float(rows[i - 1].get(metric, 0.0)) if i > 0 else None
                nxt = float(rows[i + 1].get(metric, 0.0)) if i + 1 < len(rows) else None
                q4_med = q4_medians[metric]

                # Suspicious zero between non-zero neighbors, or immediately
                # after a large prior value.
                between_nonzero = prev is not None and nxt is not None and prev > 0 and nxt > 0 and cur == 0.0
                dropped_to_zero = prev is not None and prev > 1e8 and cur == 0.0
                if between_nonzero or dropped_to_zero:
                    flags.append({
                        "company": company_name,
                        "entity": entity,
                        "period": period,
                        "metric": metric,
                        "severity": "high",
                        "issue": "suspicious_zero",
                        "current_value": cur,
                        "prev_value": prev,
                        "next_value": nxt,
                        "q4_median": q4_med,
                        "ratio": (cur / prev) if prev else 0.0,
                    })
                    continue

                # Large quarter-over-quarter drop for material balances.
                if prev is not None and prev > 1e8 and cur > 0:
                    ratio = cur / prev if prev else 0.0
                    if ratio < 0.25:
                        flags.append({
                            "company": company_name,
                            "entity": entity,
                            "period": period,
                            "metric": metric,
                            "severity": "high",
                            "issue": "drop_vs_prev",
                            "current_value": cur,
                            "prev_value": prev,
                            "next_value": nxt,
                            "q4_median": q4_med,
                            "ratio": ratio,
                        })

                # Soft warning vs historical Q4 baseline.
                if q4_med > 1e8 and cur > 0:
                    ratio_q4 = cur / q4_med
                    if ratio_q4 < 0.35:
                        flags.append({
                            "company": company_name,
                            "entity": entity,
                            "period": period,
                            "metric": metric,
                            "severity": "medium",
                            "issue": "low_vs_q4_median",
                            "current_value": cur,
                            "prev_value": prev,
                            "next_value": nxt,
                            "q4_median": q4_med,
                            "ratio": ratio_q4,
                        })

    return flags


def write_quality_flags(flags: list[dict[str, Any]], out_dir: Path) -> None:
    """Write quality flags to JSON/CSV for frontend warning badges."""
    json_out = out_dir / "quality_flags.json"
    json_out.write_text(json.dumps(flags, indent=2), encoding="utf-8")

    csv_out = out_dir / "quality_flags.csv"
    with csv_out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=QUALITY_HEADER)
        w.writeheader()
        for r in flags:
            w.writerow({k: r.get(k, "") for k in QUALITY_HEADER})


def process_company(
    company_name: str,
    txt_dir: Path,
    out_dir: Path,
    entities: list[str],
) -> list[dict]:
    """Extract KPIs for all entities of a company. Returns all records."""
    print(f"\n{company_name}")
    all_records: list[dict] = []

    for entity in entities:
        files = sorted(txt_dir.glob(f"{entity}_*.txt"))
        if not files:
            print(f"  {entity}: no text files found")
            continue

        print(f"\n  -- {entity} ({len(files)} periods) --")
        records = []
        for f in files:
            rec = extract_period(f, entity)
            records.append(rec)
            bonds_b = rec["bonds"] / 1e9
            mort_b  = rec["mortgages"] / 1e9
            ann_b   = rec["annuity_ytd"] / 1e9
            print(f"    {rec['period']:8s}  bonds={bonds_b:7.2f}B  "
                  f"mort={mort_b:6.2f}B  annuity={ann_b:5.2f}B")
            if rec["bonds"] == 0 and rec["mortgages"] == 0:
                print(f"    WARNING: {entity} {rec['period']} - no bond/mortgage data")

        records.sort(key=lambda r: r["period"])
        write_timeseries(records, out_dir, entity)
        all_records.extend(records)

    if all_records:
        all_records.sort(key=lambda r: (r["entity"], r["period"]))
        write_timeseries(all_records, out_dir, "all")
        print(f"\n  Combined: {len(all_records)} records -> all_timeseries.json/csv")
        flags = detect_quality_flags(company_name, all_records)
        write_quality_flags(flags, out_dir)
        print(f"  Quality: {len(flags)} flags -> quality_flags.json/csv")

    return all_records
