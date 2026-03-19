"""
Extract time-series KPIs from all historical AAIA quarterly text files.
Outputs historical/timeseries.json and historical/timeseries.csv.

Extracted KPIs per period:
  - Bonds (Schedule D verification ending BV)
  - Mortgage loans (Schedule B verification ending BV)
  - Other long-term assets (Schedule BA verification ending BV)
  - Cash equivalents (Schedule E Part 2 ending BV)
  - Real estate (Schedule A verification ending BV)
  - Annuity considerations YTD (Schedule T total)
  - Life premiums YTD (Schedule T total)
"""

import csv
import json
import re
from pathlib import Path

BASE    = Path(__file__).resolve().parent
TXT_DIR = BASE / "historical" / "extracted"
OUT_DIR = BASE / "historical"

NUMBER_RE = re.compile(r"\(?\d[\d,]*(?:\.\d+)?\)?")

VALID_STATE_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL",
    "GA","HI","ID","IL","IN","IA","KS","KY","LA","ME",
    "MD","MA","MI","MN","MS","MO","MT","NE","NV","NH",
    "NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI",
    "SC","SD","TN","TX","UT","VT","VA","WA","WV","WI",
    "WY","PR","VI","GU","MP","AS",
}


def parse_num(s: str) -> float:
    if not s or not s.strip():
        return 0.0
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.replace("(","").replace(")","").replace(",","").strip()
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return 0.0


def first_number(text: str) -> float:
    m = NUMBER_RE.search(text)
    return parse_num(m.group()) if m else 0.0


# ---------------------------------------------------------------------------
# Verification schedule extractor
# Finds the block "SCHEDULE X - VERIFICATION" and extracts line items.
# Returns {line_id: {"ytd": float, "prior": float}}
# ---------------------------------------------------------------------------

def extract_verification(text: str, schedule_header: str) -> dict:
    """
    Looks for schedule_header in text, then scans for numbered rows like:
      "  1.  Description ....  123,456   789,012"
    Returns {line_id: {"ytd": float, "prior": float}}
    """
    idx = text.find(schedule_header)
    if idx == -1:
        return {}

    # Find the end of this block: the next schedule header (at least 200 chars ahead)
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

        # Extract all numbers from the tail, then filter out small reference integers.
        # Verification schedule totals are always >= 1,000 (usually billions).
        # Line references like "11" or "12" in descriptions are small and have no commas.
        nums = NUMBER_RE.findall(tail)
        nums = [n for n in nums if any(c.isdigit() for c in n) and
                (',' in n or len(n.replace('(','').replace(')','')) >= 5)]
        if len(nums) >= 2:
            result[lid] = {"ytd": parse_num(nums[0]), "prior": parse_num(nums[1])}
        elif len(nums) == 1:
            result[lid] = {"ytd": parse_num(nums[0]), "prior": 0.0}
    return result


def ending_bv(lines: dict, preferred_ids: list) -> float:
    """Return the first matching line_id value from lines dict."""
    for lid in preferred_ids:
        if lid in lines:
            return lines[lid]["ytd"]
    return 0.0


# ---------------------------------------------------------------------------
# Schedule T extractor — sum all valid state rows
# ---------------------------------------------------------------------------

SCHED_T_ROW = re.compile(
    r"^\s*\d+\.\s+.+?"        # ordinal + name
    r"\s*\.{5,}\s*"            # dot separator
    r"([A-Z]{2,3})"            # state code
    r"\s*\.+\s*[A-Z]+"        # status
    r"\s*\.+\s*"
    r"(.+)$"                   # numeric tail
)


def extract_schedule_t(text: str) -> tuple[float, float]:
    """Returns (annuity_total, life_premiums_total) from Schedule T."""
    idx = text.find("SCHEDULE T")
    if idx == -1:
        return 0.0, 0.0

    block = text[idx: idx + 30000]
    started = False
    annuity = 0.0
    life    = 0.0

    for line in block.splitlines():
        if not started:
            if "States, Etc." in line or "STATES, ETC" in line.upper():
                started = True
            continue
        if "DETAILS OF WRITE-INS" in line.upper():
            break

        m = SCHED_T_ROW.match(line)
        if not m:
            continue
        code = m.group(1).upper()
        if code not in VALID_STATE_CODES:
            continue

        nums = NUMBER_RE.findall(m.group(2))
        nums = [parse_num(n) for n in nums if any(c.isdigit() for c in n)]
        # Schedule T columns: life_prem, annuity_consid, A&H, other, total, deposit
        if len(nums) >= 2:
            life    += nums[0]
            annuity += nums[1]

    return annuity, life


# ---------------------------------------------------------------------------
# Main extractor per period
# ---------------------------------------------------------------------------

def extract_period(txt_path: Path) -> dict | None:
    period = txt_path.stem.replace("AAIA_", "")
    text = txt_path.read_text(encoding="utf-8", errors="ignore")

    result = {"period": period}

    # Bonds — Schedule D verification
    d_lines = extract_verification(text, "SCHEDULE D - VERIFICATION")
    result["bonds"] = ending_bv(d_lines, ["13", "11", "12", "10"])

    # Mortgages — Schedule B verification
    b_lines = extract_verification(text, "SCHEDULE B - VERIFICATION")
    result["mortgages"] = ending_bv(b_lines, ["13", "15", "11", "12"])

    # Other long-term assets — Schedule BA verification
    ba_lines = extract_verification(text, "SCHEDULE BA - VERIFICATION")
    result["alts"] = ending_bv(ba_lines, ["13", "11", "12"])

    # Cash equivalents — Schedule E Part 2 verification
    e_lines = extract_verification(text, "SCHEDULE E - PART 2 - VERIFICATION")
    if not e_lines:
        e_lines = extract_verification(text, "SCHEDULE E - VERIFICATION")
    result["cash"] = ending_bv(e_lines, ["12", "10", "11", "13"])

    # Real estate — Schedule A verification
    a_lines = extract_verification(text, "SCHEDULE A - VERIFICATION")
    result["real_estate"] = ending_bv(a_lines, ["11", "9", "10", "13"])

    # Schedule T
    annuity, life = extract_schedule_t(text)
    result["annuity_ytd"]    = annuity
    result["life_prem_ytd"]  = life

    result["total_invested"] = (
        result["bonds"] + result["mortgages"] + result["alts"] +
        result["cash"] + result["real_estate"]
    )

    # Only return if we got at least bonds or mortgages
    if result["bonds"] == 0 and result["mortgages"] == 0:
        print(f"  WARNING: {period} — no bond/mortgage data found")

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

HEADER = [
    "period", "bonds", "mortgages", "alts", "cash", "real_estate",
    "total_invested", "annuity_ytd", "life_prem_ytd",
]


def main():
    txt_files = sorted(TXT_DIR.glob("AAIA_*.txt"))
    if not txt_files:
        print("No extracted text files found in historical/extracted/")
        return

    print(f"Processing {len(txt_files)} period files...\n")
    records = []

    for f in txt_files:
        rec = extract_period(f)
        if rec:
            records.append(rec)
            print(f"  {rec['period']:8s}  bonds={rec['bonds']/1e9:7.1f}B  "
                  f"mort={rec['mortgages']/1e9:7.1f}B  "
                  f"annuity={rec['annuity_ytd']/1e9:6.1f}B")

    # Sort chronologically
    records.sort(key=lambda r: r["period"])

    # Write JSON
    json_out = OUT_DIR / "timeseries.json"
    json_out.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"\nWrote {json_out} ({len(records)} periods)")

    # Write CSV
    csv_out = OUT_DIR / "timeseries.csv"
    with csv_out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in records:
            w.writerow({k: r.get(k, "") for k in HEADER})
    print(f"Wrote {csv_out}")


if __name__ == "__main__":
    main()
