"""
Download Corebridge Financial statutory filings for three subsidiaries:
  AGL   - American General Life Insurance Company         (TX, NAIC 60488)
  VALIC - The Variable Annuity Life Insurance Company     (TX, NAIC 70238)
  USL   - United States Life Insurance Company in the City of New York (NY, NAIC 70106)

Saves PDFs to companies/corebridge/pdfs/ and extracts text to
companies/corebridge/extracted/.

CDN: https://s201.q4cdn.com/405089319/files/
Note: CRBG went public in September 2022 (spun off from AIG).
Coverage goes back to 2021 for most entities.
Only annual statements are publicly posted (no quarterly).
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "corebridge" / "pdfs"
TXT_DIR = BASE / "companies" / "corebridge" / "extracted"

CDN = "https://s201.q4cdn.com/405089319/files"

FILINGS = [
    # -- American General Life Insurance Company (AGL) ----------------------
    ("AGL", "2025Q4", f"{CDN}/doc_downloads/2026/03/60488-AGL-2025-Annual-Statement.pdf"),
    ("AGL", "2024Q4", f"{CDN}/doc_downloads/2025/03/60488-AGL-2024-Annual-Statement.pdf"),
    ("AGL", "2023Q4", f"{CDN}/doc_downloads/2024/60488-agl-2023-annual-statement.pdf"),
    ("AGL", "2022Q4", f"{CDN}/doc_downloads/statutory_statement/American-General-Life-2022-Annual-Statement.pdf"),
    ("AGL", "2021Q4", f"{CDN}/doc_financials/2022/statutory_statements/agl-4q21-financial-statement-book-1-of-2.pdf"),

    # -- The Variable Annuity Life Insurance Company (VALIC) ----------------
    ("VALIC", "2025Q4", f"{CDN}/doc_downloads/2026/03/70238-VALIC-2025-Annual-Statement.pdf"),
    ("VALIC", "2024Q4", f"{CDN}/doc_downloads/2025/03/70238-VALIC-2024-Annual-Statement.pdf"),
    ("VALIC", "2023Q4", f"{CDN}/doc_downloads/2024/70238-valic-2023-annual-statement.pdf"),
    ("VALIC", "2022Q4", f"{CDN}/doc_downloads/statutory_statement/The-Variable-Annuity-Life-Insurance-Company-2022-Annual-Report.pdf"),
    ("VALIC", "2021Q4", f"{CDN}/doc_financials/2022/statutory_statements/valic-4q21-financial-statement.pdf"),

    # -- United States Life Insurance Company in the City of New York (USL) --
    ("USL", "2025Q4", f"{CDN}/doc_downloads/2026/03/70106-USL-2025-Annual-Statement.pdf"),
    ("USL", "2024Q4", f"{CDN}/doc_downloads/2025/03/70106-USL-2024-Annual-Statement.pdf"),
    ("USL", "2023Q4", f"{CDN}/doc_downloads/2024/70106-usl-2023-annual-statement.pdf"),
    ("USL", "2022Q4", f"{CDN}/doc_downloads/statutory_statement/The-United-States-Life-Insurance-Company-in-the-City-of-New-York-2022-Annual-Statement.pdf"),
    ("USL", "2021Q4", f"{CDN}/doc_financials/2022/statutory_statements/usl-4q21-financial-statement.pdf"),
]


def main():
    run_pipeline(
        "Corebridge Financial", FILINGS, PDF_DIR, TXT_DIR,
        note="Only annual statements are publicly posted (no quarterly).",
    )


if __name__ == "__main__":
    main()
