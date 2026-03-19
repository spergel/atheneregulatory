"""
Download Lincoln National statutory filings for two subsidiaries:
  LNL   - The Lincoln National Life Insurance Company
  LLANY - Lincoln Life & Annuity Company of New York

Saves PDFs to companies/lincoln/pdfs/ and extracts text to
companies/lincoln/extracted/.

Note: Lincoln only publishes ANNUAL statutory statements publicly.
No quarterly statements are posted on their IR site.
Coverage: LNL 2019-2023, LLANY 2020-2023 (2024 annual expected ~March 2025).
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "lincoln" / "pdfs"
TXT_DIR = BASE / "companies" / "lincoln" / "extracted"

# (entity, period, url)
FILINGS = [
    # -- The Lincoln National Life Insurance Company (LNL) ------------------
    ("LNL", "2023Q4", "https://www.lincolnfinancial.com/pbl-static/pdf/LNL-Statutory-Statement-2023.pdf"),
    ("LNL", "2022Q4", "https://www.lincolnfinancial.com/pbl-static/pdf/LNL-Statutory-Statement-2022.pdf"),
    ("LNL", "2021Q4", "https://www.lincolnfinancial.com/pbl-static/pdf/LNL-Statutory-Statement-2021.pdf"),
    ("LNL", "2020Q4", "https://www.lincolnfinancial.com/pbl-static/pdf/LNL-Statutory-Statement-2020.pdf"),
    ("LNL", "2019Q4", "https://www.lincolnfinancial.com/pbl-static/pdf/LNL-Statutory-Statement-2019.pdf"),

    # -- Lincoln Life & Annuity Company of New York (LLANY) -----------------
    ("LLANY", "2023Q4", "https://www.lincolnfinancial.com/pbl-static/pdf/LLANY-Statutory-Statement-2023.PDF"),
    ("LLANY", "2022Q4", "https://www.lincolnfinancial.com/pbl-static/pdf/LLANY-Statutory-Statement-2022.pdf"),
    ("LLANY", "2021Q4", "https://www.lincolnfinancial.com/pbl-static/pdf/LLANY-Statutory-Statement-2021.pdf"),
    ("LLANY", "2020Q4", "https://www.lfg.com/wcs-static/pdf/2020%20LLANY%20Statutory%20Statement.pdf"),
]


def main():
    run_pipeline(
        "Lincoln National", FILINGS, PDF_DIR, TXT_DIR,
        note="Only annual statements are published publicly (no quarterly).",
    )


if __name__ == "__main__":
    main()
