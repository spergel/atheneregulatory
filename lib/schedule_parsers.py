"""
Parsers for NAIC statutory filing schedules extracted from PDF text.

Handles the dot-padded fixed-width format produced by `pdftotext -layout`.
All parsers are tolerant of missing/blank columns and multi-page sections.
"""

import re
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_dots(line: str) -> list[str]:
    """Replace dot-runs with spaces and split into tokens."""
    return re.sub(r'\.{2,}', ' ', line).split()


def _to_int(s: str) -> int:
    """Parse a possibly-parenthesized or comma-formatted integer."""
    s = s.replace(',', '').strip()
    if s.startswith('(') and s.endswith(')'):
        return -int(s[1:-1])
    try:
        return int(s)
    except ValueError:
        return 0


def _to_float(s: str) -> float:
    try:
        return float(s.replace(',', ''))
    except ValueError:
        return 0.0


DATE_RE = re.compile(r'\d{2}/\d{2}/\d{4}')

# All valid USPS state and territory codes.
# Used to distinguish real state fields from city-name words that happen to be
# 2-3 uppercase letters (e.g. "SAN" in "San Francisco", "NEW" in "New York").
_US_STATE_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM",
    "NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA",
    "WV","WI","WY","PR","VI","GU","MP","AS",
}

# Country / jurisdiction codes used in NAIC Schedule BA filings.
# 2-char: FE = "Foreign Entity" (NAIC catch-all for foreign domicile).
# 3-char: ISO/FIPS codes commonly seen in Schedule BA state-of-domicile columns.
_BA_COUNTRY_CODES = {
    "FE",
    "CYM","LUX","GBR","CAN","IRL","NLD","DEU","FRA","GGY","JEY",
    "BMU","VGB","CHE","AUS","JPN","SGP","KOR","BRA","ISR","SWE",
    "DNK","NOR","FIN","AUT","BEL","ITA","ESP","PRT","NZL","HKG",
    "TWN","CHN","IND","ZAF","MEX","ARG","COL","CHL","CRI",
    "PAN","MUS","MLT","LIE","MCO","GIB","IMN","ABW","BHS",
}

# Combined set used to validate state/country codes in Schedule BA rows.
_BA_STATE_CODES = _US_STATE_CODES | _BA_COUNTRY_CODES

# Embedded NAIC reference numbers: pure-digit 5-9 chars, or private-placement
# IDs that start with "1B" (e.g. "1BA466452", "1BAN0PGV7").
_BA_REF_NUM_RE = re.compile(r'^(\d{5,9}|1B[A-Z0-9]{5,9})$')

# CUSIP identifier pattern as it appears in the filing's first column.
# CUSIPs always contain at least one hyphen (e.g. "74983M-AE-7", "1BA466-45-2").
_BA_CUSIP_RE = re.compile(r'^[A-Z0-9#@]{2,9}-[A-Z0-9]{1,3}(-[A-Z0-9]+)?$')


def _extract_city_state(tokens: list[str], date_acq_idx: int) -> tuple[str, str]:
    """
    Extract (city, state) from the token slice between loan-number and date-acquired.

    Strategy: scan BACKWARDS from the date — the rightmost token that is a valid
    US state/territory code is the state; everything before it (after token[0])
    is the city.  This correctly handles multi-word cities like:
        SAN FRANCISCO CA → city='San Francisco', state='CA'
        GREEN BAY WI     → city='Green Bay',     state='WI'
        NEW YORK NY      → city='New York',       state='NY'

    For non-US entries (e.g. 'GBR', 'CAN') that aren't in the state-code set,
    fall back to the original forwards scan so those rows still parse.
    """
    # Backwards scan: prefer a valid US state code closest to the date
    for i in range(date_acq_idx - 1, 0, -1):
        t = tokens[i]
        if t in _US_STATE_CODES:
            city = ' '.join(tokens[1:i]).title()
            return city, t

    # Fallback (non-US / foreign loans): forwards scan for any 2-3 letter code
    for i in range(1, date_acq_idx):
        t = tokens[i]
        if re.match(r'^[A-Z]{2,3}$', t) and not t.isdigit():
            city = ' '.join(tokens[1:i]).title()
            return city, t

    return '', ''


def _header_to_regex(header: str) -> re.Pattern[str]:
    """
    Convert an expected schedule header into a whitespace-robust, case-insensitive regex.

    This is important because pdftotext output often varies in:
      - capitalization (e.g. "Schedule" vs "SCHEDULE")
      - spacing (multiple spaces around hyphens/columns)
    """
    tokens = header.split()
    # Join tokens with flexible whitespace; keep punctuation tokens (e.g. "-") escaped.
    pattern = r'\s+'.join(re.escape(t) for t in tokens)
    return re.compile(pattern, flags=re.IGNORECASE)


def _find_section(text: str, header: str, stop_headers: list[str]) -> str:
    """
    Return the slice of text from `header` up to the first `stop_headers` match.
    Returns '' if not found.
    """
    header_re = _header_to_regex(header)
    start_m = header_re.search(text)
    if not start_m:
        return ''

    start = start_m.start()
    end = len(text)

    search_from = start_m.end()
    for stop in stop_headers:
        stop_re = _header_to_regex(stop)
        m = stop_re.search(text, search_from)
        if m and m.start() < end:
            end = m.start()

    return text[start:end]


def _all_section_pages(text: str, header: str,
                        stop_headers: list[str] | None = None) -> str:
    """
    Return concatenated content of ALL occurrences of `header` in the text.
    Used when a schedule spans multiple printed pages (each with the same header).

    stop_headers: for the last page only (which would otherwise extend to EOF),
    limit it to the first occurrence of any stop header after the last match.
    """
    header_re = _header_to_regex(header)
    matches = list(header_re.finditer(text))
    if not matches:
        return ''

    parts: list[str] = []
    for i, m in enumerate(matches):
        start = m.start()
        # Default end: start of next same-header occurrence, or EOF
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        # Further limit by stop_headers on every page (not just the last).
        # This prevents a single large page from bleeding into other schedules
        # when the next same-header occurrence is far away.
        if stop_headers:
            for stop in stop_headers:
                stop_re = _header_to_regex(stop)
                sm = stop_re.search(text, m.end())
                if sm and sm.start() < end:
                    end = sm.start()
        parts.append(text[start:end])
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Schedule T — Premiums and Annuity Considerations by State
# ---------------------------------------------------------------------------

def parse_schedule_t(text: str) -> list[dict[str, Any]]:
    """
    Parse Schedule T (Premiums and Annuity Considerations).

    Returns list of dicts:
      state, state_code, life, annuity, ah, other, total, deposit
    """
    section = _find_section(
        text,
        'SCHEDULE T - PREMIUMS',
        ['SCHEDULE U', 'SCHEDULE Y', 'SCHEDULE D - PART', 'SCHEDULE B - PART'],
    )
    if not section:
        return []

    rows = []
    for line in section.splitlines():
        # State rows start with a row number then a period
        if not re.match(r'^\s*\d+\.\s+\S', line):
            continue

        tokens = _strip_dots(line)
        if len(tokens) < 5:
            continue

        # Find the 2-letter state code in the token list
        state_code_idx = None
        for i, t in enumerate(tokens):
            if len(t) == 2 and t.isupper() and t.isalpha() and i > 0:
                state_code_idx = i
                break
        if state_code_idx is None:
            continue

        state_code = tokens[state_code_idx]
        # State name is tokens[1..state_code_idx-1] (skip the leading row number)
        state_name = ' '.join(tokens[1:state_code_idx])

        # Remaining tokens after state code: license status (L or NL), then numbers
        rest = tokens[state_code_idx + 1:]
        # Drop the license status token (one or two chars)
        if rest and re.match(r'^[A-Z]{1,2}$', rest[0]):
            rest = rest[1:]

        # Parse numeric tokens
        nums = []
        for t in rest:
            if re.match(r'^[\d,()]+$', t):
                nums.append(_to_int(t))
            else:
                break  # stop at non-numeric

        if len(nums) < 2:
            continue

        # Identify the total column: find index i where sum(nums[:i]) == nums[i]
        total_idx = None
        for i in range(1, len(nums)):
            if nums[i] == sum(nums[:i]):
                total_idx = i
                break

        if total_idx is None:
            # Fallback: second-to-last is total if deposit follows, else last is total
            total_idx = len(nums) - 1

        data = nums[:total_idx]
        total = nums[total_idx]
        deposit = nums[total_idx + 1] if total_idx + 1 < len(nums) else 0

        rows.append({
            'state': state_name.title(),
            'state_code': state_code,
            'life': data[0] if len(data) > 0 else 0,
            'annuity': data[1] if len(data) > 1 else 0,
            'ah': data[2] if len(data) > 2 else 0,
            'other': data[3] if len(data) > 3 else 0,
            'total': total,
            'deposit': deposit,
        })

    return rows


# ---------------------------------------------------------------------------
# Schedule B Part 1 — Individual Mortgage Loans
# ---------------------------------------------------------------------------

# Subtotal / section-break lines (e.g. "0199999. Mortgages in good standing")
_B_SUBTOTAL_RE = re.compile(r'^\s*[0-9]+9{4,}\.')


def parse_schedule_b(text: str) -> list[dict[str, Any]]:
    """
    Parse Schedule B Part 1 (Individual Mortgage Loans Owned).

    Returns list of dicts:
      loan_number, city, state, date_acquired, interest_rate,
      book_value, land_value, appraisal_date
    """
    def parse_part1(section_text: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in section_text.splitlines():
            # Skip blank lines, headers, and subtotals
            stripped = line.strip()
            if not stripped:
                continue
            if _B_SUBTOTAL_RE.match(stripped):
                continue
            if 'SCHEDULE B' in stripped or 'Showing' in stripped or stripped.startswith('1 ') or stripped[0].isalpha():
                continue

            # Individual loan lines must contain at least one date
            dates = DATE_RE.findall(re.sub(r'\.{2,}', ' ', line))
            if len(dates) < 1:
                continue

            tokens = _strip_dots(line)
            if len(tokens) < 6:
                continue

            # Loan number is the first token (alphanumeric, may have letter suffix)
            loan_number = tokens[0]
            if not re.match(r'^[A-Z0-9]{4,}$', loan_number.upper()):
                continue

            # Find date-acquired index (first date in tokens)
            date_acq_idx = None
            for i, t in enumerate(tokens):
                if DATE_RE.match(t):
                    date_acq_idx = i
                    break
            if date_acq_idx is None:
                continue

            # State and city — scan backwards so multi-word city names parse correctly
            city, state = _extract_city_state(tokens, date_acq_idx)

            # Interest rate: first float token after the date
            rate = 0.0
            book_value = 0
            land_value = 0
            appraisal_date = ''

            post_date = tokens[date_acq_idx + 1:]
            # Find rate (first float), then numbers, then appraisal date (last date)
            rate_found = False
            numeric_vals: list[int] = []
            appraisal_date = dates[-1] if len(dates) > 1 else ''

            for t in post_date:
                if not rate_found and re.match(r'^\d+\.\d+$', t):
                    rate = _to_float(t)
                    rate_found = True
                    continue
                if rate_found:
                    if DATE_RE.match(t):
                        appraisal_date = t
                        break
                    if re.match(r'^[\d,()]+$', t):
                        numeric_vals.append(_to_int(t))

            book_value = numeric_vals[0] if numeric_vals else 0
            # Land value: last positive integer before the appraisal date
            for v in reversed(numeric_vals):
                if v > 0:
                    land_value = v
                    break

            if loan_number and rate > 0 and book_value > 0:
                rows.append({
                    'loan_number': loan_number,
                    'city': city,
                    'state': state,
                    'date_acquired': dates[0],
                    'interest_rate': rate,
                    'book_value': book_value,
                    'land_value': land_value,
                    'appraisal_date': appraisal_date,
                })

        return rows

    def parse_part3(section_text: str) -> list[dict[str, Any]]:
        """
        Schedule B Part 3 (disposed/transferred/repaid) can appear when Part 1 is absent.
        We'll do a best-effort extraction so we still return rows in the same schema,
        but leave rate/land/appraisal empty where not present in the section.
        """
        rows: list[dict[str, Any]] = []
        for line in section_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if 'SCHEDULE B' in stripped or 'Showing' in stripped:
                continue
            if _B_SUBTOTAL_RE.match(stripped):
                continue

            tokens = _strip_dots(line)
            if len(tokens) < 5:
                continue

            loan_number = tokens[0]
            if not re.match(r'^[A-Z0-9]{4,}$', loan_number.upper()):
                continue

            # Treat first date token as date acquired
            date_acq_idx = None
            for i, t in enumerate(tokens):
                if DATE_RE.match(t):
                    date_acq_idx = i
                    break
            if date_acq_idx is None:
                continue
            date_acquired = tokens[date_acq_idx]

            # State and city — scan backwards so multi-word city names parse correctly
            city, state = _extract_city_state(tokens, date_acq_idx)

            # Book value: first numeric-like value after the date
            post_date = tokens[date_acq_idx + 1:]
            numeric_vals: list[int] = []
            for t in post_date:
                if re.match(r'^[\d,()]+$', t):
                    numeric_vals.append(_to_int(t))
            book_value = numeric_vals[0] if numeric_vals else 0

            if book_value <= 0:
                continue

            rows.append({
                'loan_number': loan_number,
                'city': city,
                'state': state,
                'date_acquired': date_acquired,
                'interest_rate': 0.0,
                'book_value': book_value,
                'land_value': 0,
                'appraisal_date': '',
            })

        return rows

    # Prefer Part 1
    section1 = _all_section_pages(text, 'SCHEDULE B - PART 1')
    if section1:
        rows1 = parse_part1(section1)
        if rows1:
            return rows1

    # Fallback: some filings use SCHEDULE B - PART 2 instead of PART 1.
    section2 = _all_section_pages(text, 'SCHEDULE B - PART 2')
    if section2:
        rows2 = parse_part1(section2)
        if rows2:
            return rows2

    # Fallback to Part 3
    section3 = _all_section_pages(text, 'SCHEDULE B - PART 3')
    if not section3:
        return []
    return parse_part3(section3)


# ---------------------------------------------------------------------------
# Schedule BA Part 1 — Other Long-Term Invested Assets (Alternatives)
# ---------------------------------------------------------------------------

def _ba_clean_pending(raw: str) -> str:
    """
    Clean a BA pending-name string:
      1. Strip leading section/row codes like "E07", "2.A", "1.B".
      2. Strip trailing all-caps GP names that leaked from the adjacent column.
         Heuristic: if we see ≥ 2 consecutive all-caps words (each ≥ 4 letters)
         after at least 2 title-case (mixed-case) words, truncate there.
    """
    # 1 – strip leading section codes
    s = re.sub(r'^[A-Z]?\d+(?:\.\d+)?[A-Z]?\s+', '', raw).strip()

    # 2 – strip trailing all-caps GP name block
    tokens = s.split()
    title_seen = 0
    for i, t in enumerate(tokens):
        alpha = re.sub(r'[^A-Za-z]', '', t)
        if alpha:
            if not alpha.isupper():
                title_seen += 1
            elif alpha.isupper() and len(alpha) >= 4 and title_seen >= 2:
                # All-caps word (≥ 4 letters) after ≥ 2 title-case words →
                # the rest is probably the GP / vendor name column.
                s = ' '.join(tokens[:i]).strip()
                break
    return s


def parse_schedule_ba(text: str) -> list[dict[str, Any]]:
    """
    Parse Schedule BA Part 1 (Other Long-Term Invested Assets).

    Returns list of dicts:
      name, state, date_acquired,
      actual_cost, fair_value, book_value, investment_income, ownership_pct

    Name-parsing improvements:
    - Uses _BA_STATE_CODES (US states + FE + country codes) to validate the
      state/country token; entity-type suffixes like LP, SA, TL, II, AP, AG
      are NOT in the set and will never be mis-identified as a state.
    - Handles multi-line fund names: when a line has no date it is buffered as
      a "pending name"; the following data line uses that name if its first
      meaningful token is an embedded reference number.
    - Strips embedded NAIC reference numbers and GP names from the name field.
    """

    def parse_ba_part(part_no: int) -> list[dict[str, Any]]:
        # Stop headers prevent the last page from bleeding into subsequent
        # schedules (e.g. Schedule D Part 4 paydown rows look enough like BA
        # rows that the parser would pick them up without this guard).
        _BA_STOP_HEADERS = [
            f'SCHEDULE BA - PART {part_no + 1}',
            'SCHEDULE D -',
            'SCHEDULE C',
            'SCHEDULE E -',
            'SCHEDULE S',
            'SCHEDULE T',
        ]
        section = _all_section_pages(text, f'SCHEDULE BA - PART {part_no}',
                                     stop_headers=_BA_STOP_HEADERS)
        if not section:
            return []

        # Subtotals match patterns like "1799999." or "1899999."
        subtotal_re = re.compile(r'^\s*[0-9]+9{3,}\.')

        # Header keywords that should never be treated as pending fund names
        _SKIP_KEYWORDS = ('SCHEDULE', 'Showing', 'NAIC', 'fication', 'strative',
                          'Symbol', 'Partner', 'Identi', 'Strategy', 'Encum',
                          'Unrealized', 'Carrying', 'Valuation', 'Impairment',
                          'Temporary', 'Adjusted', 'Amortization', 'Contractual',
                          'Effective', 'stricted', 'stration', 'Stated',
                          'Admini-', 'Admini')

        rows: list[dict[str, Any]] = []
        pending_name = ''

        for line in section.splitlines():
            stripped = line.strip()
            if not stripped:
                continue   # blank lines do NOT clear pending_name
            if subtotal_re.match(stripped):
                pending_name = ''
                continue
            if 'SCHEDULE BA' in stripped or 'Showing' in stripped:
                continue

            tokens = _strip_dots(line)
            if len(tokens) < 4:
                continue

            # Locate the first date token (4-digit year required)
            date_acq_idx = None
            for i, t in enumerate(tokens):
                if DATE_RE.match(t):
                    date_acq_idx = i
                    break

            if date_acq_idx is None:
                # No date → potential name-only continuation line; buffer it.
                candidate = ' '.join(tokens).strip()
                # Reject obvious column-header fragments
                if any(kw in candidate for kw in _SKIP_KEYWORDS):
                    continue
                # Reject lines that look like wrapped numeric data (>50% digits/punct)
                alpha_chars = sum(c.isalpha() for c in candidate)
                if alpha_chars < len(candidate) * 0.35:
                    continue
                pending_name = candidate
                continue

            # ----------------------------------------------------------------
            # Find state/country code using the validated code set.
            # Scan backwards from the date so LP, SA, TL, II etc. that appear
            # in fund names are never mistaken for state/country codes.
            # ----------------------------------------------------------------
            state = ''
            name_end = date_acq_idx
            for i in range(date_acq_idx - 1, 0, -1):
                t = tokens[i]
                if t in _BA_STATE_CODES:
                    state = t
                    name_end = i
                    break

            # Determine whether tokens[0] is a CUSIP or part of the fund name.
            # CUSIPs always have hyphens; when the CUSIP column is blank the
            # first fund-name word becomes tokens[0] and must be included.
            name_start = 1 if (tokens and _BA_CUSIP_RE.match(tokens[0])) else 0

            # Raw slice between name-start and the state/country code.
            raw_name_tokens = tokens[name_start:name_end]

            # Truncate at the first embedded NAIC reference number; everything
            # after it (city tokens, etc.) is location/GP data, not the name.
            refnum_stop = len(raw_name_tokens)
            for _i, _t in enumerate(raw_name_tokens):
                if _BA_REF_NUM_RE.match(_t):
                    refnum_stop = _i
                    break
            name_tokens = raw_name_tokens[:refnum_stop]
            extracted_name = ' '.join(name_tokens).strip()

            # ----------------------------------------------------------------
            # Resolve final name, handling the multi-line case.
            # ----------------------------------------------------------------
            if pending_name:
                clean_pending = _ba_clean_pending(pending_name)
                first_token = tokens[0] if tokens else ''
                if _BA_REF_NUM_RE.match(first_token):
                    # Data line begins with a reference number → the full fund
                    # name was on the previous (pending) line.
                    name = clean_pending
                elif extracted_name:
                    # Data line has additional name tokens → combine.
                    name = (clean_pending + ' ' + extracted_name).strip()
                else:
                    name = clean_pending
            else:
                name = extracted_name

            pending_name = ''

            # ----------------------------------------------------------------
            # Parse numeric values after the date.
            # ----------------------------------------------------------------
            post_date = tokens[date_acq_idx + 1:]
            numeric_vals: list[int] = []
            ownership = 0.0
            _type_skipped = False  # skip the single-digit Type/Strategy code (e.g. "3")
            for t in post_date:
                if re.match(r'^\d+\.\d{3}$', t):   # ownership% has 3 decimal places
                    ownership = _to_float(t)
                elif re.match(r'^[1-9]$', t) and not _type_skipped and not numeric_vals:
                    # First single-digit token before any monetary values is the
                    # Type/Strategy column code used in BA Part 2/3 (1=VC, 2=LBO, etc.)
                    _type_skipped = True
                elif re.match(r'^[\d,()]+$', t):
                    numeric_vals.append(_to_int(t))

            actual_cost = numeric_vals[0] if len(numeric_vals) > 0 else 0
            fair_value  = numeric_vals[1] if len(numeric_vals) > 1 else 0
            book_value  = numeric_vals[2] if len(numeric_vals) > 2 else 0
            # Column layout after [cost, fair, book]:
            #   …[change cols]… | Investment Income (col 19) | [Additional Investment (col 20)]
            # When col 20 is present (len ≥ 6): income = second-to-last.
            # When col 20 is absent  (len == 5): income = last (not second-to-last, which
            #   would be the total-change column and can be large and negative).
            if len(numeric_vals) >= 6:
                income = numeric_vals[-2]
            elif len(numeric_vals) == 5:
                income = numeric_vals[-1]
            else:
                income = 0

            if not name:
                continue

            if actual_cost == 0 and ownership == 0.0:
                continue

            # For parts other than 1, numeric column layout differs; zero out
            # the columns we can't reliably map.
            if part_no == 1:
                fair_out   = fair_value
                book_out   = book_value
                income_out = income
            else:
                fair_out   = 0
                book_out   = 0
                income_out = 0

            rows.append({
                'name': name,
                'state': state,
                'date_acquired': tokens[date_acq_idx],
                'actual_cost': actual_cost,
                'fair_value': fair_out,
                'book_value': book_out,
                'investment_income': income_out,
                'ownership_pct': ownership,
            })

        return rows

    # Prefer Part 1, then fall back to Parts 2/3.
    rows1 = parse_ba_part(1)
    if rows1:
        return rows1

    for part_no in (2, 3):
        rows = parse_ba_part(part_no)
        if rows:
            return rows

    return []


# ---------------------------------------------------------------------------
# Schedule D Part 1A — Bond Quality Distribution Summary
# ---------------------------------------------------------------------------

_NAIC_CAT_RE = re.compile(r'^\s*\d+\.\d+\s+NAIC\s+[1-6]')

def parse_schedule_d_quality(text: str) -> list[dict[str, Any]]:
    """
    Parse Schedule D Part 1A Section 1 (Bond Quality/Maturity Distribution).

    Returns list of dicts:
      category, naic_designation, total_current_year, total_prior_year
    """
    def parse_part1a(section_text: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        current_category = ''
        for line in section_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            # Category headers like "1. U.S. Governments"
            cat_m = re.match(r'^\s*(\d+)\.\s+(.+?)$', line)
            if cat_m and not re.match(r'^\s*\d+\.\d+', line):
                current_category = cat_m.group(2).strip()
                continue

            if not _NAIC_CAT_RE.match(line):
                continue

            tokens = _strip_dots(line)
            if len(tokens) < 4:
                continue

            # tokens[0] like "1.1", tokens[1] like "NAIC", tokens[2] like "1"
            naic_des = f"NAIC {tokens[2]}" if len(tokens) > 2 else tokens[1]
            nums = [_to_int(t) for t in tokens[3:] if re.match(r'^[\d,]+$', t)]

            # Column 7 = Total Current Year
            # Column 9 = Total Prior Year
            total_curr = nums[5] if len(nums) > 5 else 0
            total_prior = nums[7] if len(nums) > 7 else 0

            rows.append({
                'category': current_category,
                'naic_designation': naic_des,
                'total_current_year': total_curr,
                'total_prior_year': total_prior,
            })

        return rows

    section = _find_section(
        text,
        'SCHEDULE D - PART 1A - SECTION 1',
        ['SCHEDULE D - PART 1A - SECTION 2', 'SCHEDULE D - PART 2'],
    )
    if section:
        return parse_part1a(section)

    # Corebridge filings sometimes omit the "- SECTION 1" part of the header.
    section_a = _find_section(
        text,
        'SCHEDULE D - PART 1A',
        ['SCHEDULE D - PART 2', 'SCHEDULE D - PART 3', 'SCHEDULE DA', 'SCHEDULE DB'],
    )
    if section_a:
        rows_a = parse_part1a(section_a)
        if rows_a:
            return rows_a

    # Fallback: some filings only contain the bond quality distribution in Part 1B.
    # We'll parse NAIC 1..6 rows and use the last two numeric columns as:
    #  - current quarter value (2nd last numeric)
    #  - prior year value (last numeric)
    section_b = _find_section(
        text,
        'SCHEDULE D - PART 1B',
        ['SCHEDULE D - PART 2', 'SCHEDULE DA', 'SCHEDULE D - PART 3'],
    )
    if not section_b:
        return []

    rows_b: list[dict[str, Any]] = []
    for line in section_b.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        m = re.match(r'^\s*\d+\.\s+NAIC\s+([1-6])\b', stripped)
        if not m:
            continue
        naic_num = m.group(1)

        tokens = _strip_dots(line)
        nums = [_to_int(t) for t in tokens if re.match(r'^[\d,()]+$', t)]
        if len(nums) < 2:
            continue

        total_curr = nums[-2]
        total_prior = nums[-1]
        rows_b.append({
            'category': 'BONDS',
            'naic_designation': f"NAIC {naic_num}",
            'total_current_year': total_curr,
            'total_prior_year': total_prior,
        })

    return rows_b
