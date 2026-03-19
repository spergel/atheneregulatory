"""
Download Principal Financial statutory filings:
  PLIC - Principal Life Insurance Company (IA, NAIC 61271)

Saves PDFs to companies/principal/pdfs/ and extracts text to
companies/principal/extracted/.

Host: https://investors.principal.com/static-files/{uuid}

Note: Principal uses opaque UUIDs for all documents - there is no
guessable URL pattern. To find UUIDs for additional years:
  1. Visit https://investors.principal.com/financials/statutory-filings
  2. Select the desired year from the filter
  3. Right-click the filing link -> Copy link address
  4. Extract the UUID from the URL and add it to FILINGS below.

Currently confirmed: 2025 filings only.
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "principal" / "pdfs"
TXT_DIR = BASE / "companies" / "principal" / "extracted"

BASE_URL = "https://investors.principal.com/static-files"

# (entity, period, uuid)
# Add UUIDs from the IR page year filter as you find them.
FILINGS = [
    # -- Principal Life Insurance Company (PLIC) ----------------------------
    # 2025 - confirmed from IR page
    ("PLIC", "2025Q4", "41e1ab47-17ab-43f8-b9ee-53cf92f0a413"),  # Annual
    ("PLIC", "2025Q3", "9cce2f92-6bdf-4564-b4ba-e5e28172ac9e"),
    ("PLIC", "2025Q2", "98b2ba8b-7ae4-41c5-9173-f0dbd9cd1c16"),
    ("PLIC", "2025Q1", "60a02a97-a144-420b-9692-5e56e9c42933"),
    # 2024 - add UUIDs here after visiting IR page with year filter
    # ("PLIC", "2024Q4", ""),
    # ("PLIC", "2024Q3", ""),
    # ("PLIC", "2024Q2", ""),
    # ("PLIC", "2024Q1", ""),
    # 2023 - add UUIDs here
    # ("PLIC", "2023Q4", ""),
    # ("PLIC", "2023Q3", ""),
    # ("PLIC", "2023Q2", ""),
    # ("PLIC", "2023Q1", ""),
    # 2022 - add UUIDs here
    # ("PLIC", "2022Q4", ""),
    # ("PLIC", "2022Q3", ""),
    # ("PLIC", "2022Q2", ""),
    # ("PLIC", "2022Q1", ""),
]


def main():
    active = [(e, p, f"{BASE_URL}/{uuid}") for e, p, uuid in FILINGS if uuid]
    skipped = len(FILINGS) - len(active)
    if skipped:
        print(f"  ({skipped} filings skipped - UUIDs not yet filled in)\n")
    run_pipeline("Principal Financial", active, PDF_DIR, TXT_DIR, timeout=600)


if __name__ == "__main__":
    main()
