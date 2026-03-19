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


def _all_section_pages(text: str, header: str) -> str:
    """
    Return concatenated content of ALL occurrences of `header` in the text.
    Used when a schedule spans multiple printed pages (each with the same header).
    """
    header_re = _header_to_regex(header)
    matches = list(header_re.finditer(text))
    if not matches:
        return ''

    parts: list[str] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
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

            # State: the 2-3 letter code immediately before or near the date
            state = ''
            city_parts: list[str] = []
            for i in range(1, date_acq_idx):
                t = tokens[i]
                if re.match(r'^[A-Z]{2,3}$', t) and not t.isdigit():
                    state = t
                    city_parts = tokens[1:i]
                    break

            city = ' '.join(city_parts).title() if city_parts else ''

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

            # State near the acquired date
            state = ''
            city_parts: list[str] = []
            for i in range(1, date_acq_idx):
                t = tokens[i]
                if re.match(r'^[A-Z]{2,3}$', t) and not t.isdigit():
                    state = t
                    city_parts = tokens[1:i]
                    break
            city = ' '.join(city_parts).title() if city_parts else ''

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

def parse_schedule_ba(text: str) -> list[dict[str, Any]]:
    """
    Parse Schedule BA Part 1 (Other Long-Term Invested Assets).

    Returns list of dicts:
      cusip, name, city, state, gp_name, date_acquired,
      actual_cost, fair_value, book_value, investment_income, ownership_pct
    """
    def parse_ba_part(part_no: int) -> list[dict[str, Any]]:
        section = _all_section_pages(text, f'SCHEDULE BA - PART {part_no}')
        if not section:
            return []

        # Subtotals match patterns like "1799999." or "1899999."
        subtotal_re = re.compile(r'^\s*[0-9]+9{3,}\.')

        rows: list[dict[str, Any]] = []
        for line in section.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if subtotal_re.match(stripped):
                continue
            if 'SCHEDULE BA' in stripped or 'Showing' in stripped:
                continue

            # BA rows: contain a date and (typically) an ownership percentage.
            tokens = _strip_dots(line)
            if len(tokens) < 8:
                continue

            date_acq_idx = None
            for i, t in enumerate(tokens):
                if DATE_RE.match(t):
                    date_acq_idx = i
                    break
            if date_acq_idx is None:
                continue

            # Look for state code immediately before the date.
            state = ''
            name_end = date_acq_idx
            for i in range(date_acq_idx - 1, 0, -1):
                t = tokens[i]
                if re.match(r'^[A-Z]{2}$', t):
                    state = t
                    name_end = i
                    break

            name = ' '.join(tokens[1:name_end]) if name_end > 1 else ''

            post_date = tokens[date_acq_idx + 1:]
            numeric_vals: list[int] = []
            ownership = 0.0
            for t in post_date:
                if re.match(r'^\d+\.\d{3}$', t):  # ownership% has 3 decimal places
                    ownership = _to_float(t)
                elif re.match(r'^[\d,()]+$', t):
                    numeric_vals.append(_to_int(t))

            actual_cost = numeric_vals[0] if len(numeric_vals) > 0 else 0
            fair_value = numeric_vals[1] if len(numeric_vals) > 1 else 0
            book_value = numeric_vals[2] if len(numeric_vals) > 2 else 0
            income = numeric_vals[-2] if len(numeric_vals) > 4 else 0

            if not name:
                continue

            # For parts other than 1, the numeric columns often don't align to
            # fair_value/book_value/investment_income. Keep best-effort rows, but
            # only populate those columns for Part 1.
            if part_no == 1:
                fair_out = fair_value
                book_out = book_value
                income_out = income
            else:
                fair_out = 0
                book_out = 0
                income_out = 0

            if actual_cost == 0 and ownership == 0.0:
                continue

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
