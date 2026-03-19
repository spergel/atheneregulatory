"""
Download all Jackson Financial statutory filings for two subsidiaries:
  JNLIC   - Jackson National Life Insurance Company
  JNLICNY - Jackson National Life Insurance Company of New York

Saves PDFs to companies/jackson/pdfs/ and extracts text to
companies/jackson/extracted/.

File naming: {ENTITY}_{PERIOD}.pdf / .txt  e.g. JNLIC_2024Q3.pdf
Annual statements are stored as Q4.

Note: JXN went public in September 2021 (spun off from Prudential).
Coverage on their IR CDN goes back to ~2020 with some quarterly gaps
in 2020-2022 where filings were not posted publicly.
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "jackson" / "pdfs"
TXT_DIR = BASE / "companies" / "jackson" / "extracted"

CDN = "https://s202.q4cdn.com/231638402/files/doc_downloads"

# (entity, period, url)
# Annual statements stored as Q4.
FILINGS = [
    # -- Jackson National Life Insurance Company (JNLIC) --------------------
    ("JNLIC", "2025Q3", f"{CDN}/third_quarter/2025/Jackson-National-Life-Insurance-Company-3Q-2025-Statutory-Statement.pdf"),
    ("JNLIC", "2025Q2", f"{CDN}/sec_quarter/2025/Jackson-National-Life-Insurance-Company-2Q-2025-Statutory-Statement.pdf"),
    ("JNLIC", "2025Q1", f"{CDN}/2025/05/Jackson-National-Life-Insurance-Company-1Q-2025-Statutory-Statement.pdf"),
    ("JNLIC", "2024Q4", f"{CDN}/annual/2025/Jackson-National-LIfe-Insurance-Company-4Q-2024-Statutory-Statement.pdf"),
    ("JNLIC", "2024Q3", f"{CDN}/third_quarter/2024/Jackson-National-Life-Insurance-Company-3Q-2024-Statutory-Statement.pdf"),
    ("JNLIC", "2024Q2", f"{CDN}/sec_quarter/2024/jackson-national-life-insurance-company-2q-2024-statutory-statement.pdf"),
    ("JNLIC", "2024Q1", f"{CDN}/first_quarter/2024/jackson-national-life-insurance-company-1q-2024-statutory-statement.pdf"),
    ("JNLIC", "2023Q4", f"{CDN}/annual/2024/jackson-national-life-insurance-company-2023-annual-statutory-statement.pdf"),
    ("JNLIC", "2023Q3", f"{CDN}/third_quarter/2023/jackson-national-life-insurance-company-3q-2023-statutory-statement.pdf"),
    ("JNLIC", "2023Q2", f"{CDN}/sec_quarter/2023/jackson-national-life-insurance-company-2q-2023-statutory-statement.pdf"),
    ("JNLIC", "2023Q1", f"{CDN}/first_quarter/2023/jackson-national-life-insurance-company-1q-2023-statutory-statement.pdf"),
    ("JNLIC", "2022Q4", f"{CDN}/annual/2022/jackson-national-life-insurance-company-2022-annual-statutory-statement_amended.pdf"),
    ("JNLIC", "2022Q3", f"{CDN}/third_quarter/2022/11/Jackson-National-Life-Insurance-Company-3Q-2022-statutory-statement.pdf"),
    ("JNLIC", "2022Q2", f"{CDN}/sec_quarter/2022/Jackson-National-Life-Insurance-Company-2Q-2022-statutory-statement.pdf"),
    # 2022Q1, 2021Q4, 2021Q3, 2021Q1 not found on CDN
    ("JNLIC", "2021Q2", f"{CDN}/sec_quarter/Jackson-National-Life-Insurance-Company-2Q-2021-statutory-statement.pdf"),
    # 2020Q4, 2020Q2 not found on CDN
    ("JNLIC", "2020Q3", f"{CDN}/third_quarter/jackson-3rd-qtr-2020-statement.pdf"),
    ("JNLIC", "2020Q1", f"{CDN}/first_quarter/jackson-1Q-2020-statutory-statement.pdf"),

    # -- Jackson National Life Insurance Company of New York (JNLICNY) ------
    ("JNLICNY", "2025Q3", f"{CDN}/third_quarter/2025/Jackson-National-Life-Insurance-Company-of-New-York-3Q-2025-Statutory-Statement.pdf"),
    ("JNLICNY", "2025Q2", f"{CDN}/sec_quarter/2025/Jackson-National-Life-Insurance-Company-of-New-York-2Q-2025-Statutory-Statement.pdf"),
    ("JNLICNY", "2025Q1", f"{CDN}/2025/05/Jackson-National-Life-Insurance-Company-of-New-York-1Q-2025-Statutory-Statement.pdf"),
    # 2024Q4 not found on CDN
    ("JNLICNY", "2024Q3", f"{CDN}/third_quarter/2024/Jackson-National-Life-Insurance-Company-of-New-York-3Q-2024-Statutory-Statement.pdf"),
    ("JNLICNY", "2024Q2", f"{CDN}/sec_quarter/2024/jackson-national-life-insurance-company-of-new-york-2q-2024-statutory-statement.pdf"),
    ("JNLICNY", "2024Q1", f"{CDN}/first_quarter/2024/jackson-national-life-insurance-company-of-new-york-1q-2024-statutory-statement.pdf"),
    ("JNLICNY", "2023Q4", f"{CDN}/annual/2024/jackson-national-life-insurance-company-of-new-york-2023-annual-statutory-statement.pdf"),
    ("JNLICNY", "2023Q3", f"{CDN}/third_quarter/2023/jackson-national-life-insurance-company-of-new-york-3q-2023-statutory-statement.pdf"),
    ("JNLICNY", "2023Q2", f"{CDN}/sec_quarter/2023/jackson-national-life-insurance-company-of-new-york-2q-2023-statutory-statement.pdf"),
    ("JNLICNY", "2023Q1", f"{CDN}/first_quarter/2023/jackson-national-life-insurance-company-of-new-york-1q-2023-statutory-statement.pdf"),
    ("JNLICNY", "2022Q4", f"{CDN}/2023/03/jackson-national-life-insurance-company-of-ny-2022-annual-statutory-statement.pdf"),
    ("JNLICNY", "2022Q3", f"{CDN}/third_quarter/2022/11/Jackson-National-Life-Insurance-Co.-of-New-York-3Q-2022-statutory-statement.pdf"),
    # 2022Q2, 2022Q1 not found on CDN
    ("JNLICNY", "2021Q4", f"{CDN}/annual/Jackson-of-NY-2021-Annual-Statutory-Statement.pdf"),
    ("JNLICNY", "2021Q3", f"{CDN}/third_quarter/Jackson-National-Life-Insurance-Co.-of-New-York-3Q-2021-statutory-statement.pdf"),
    # 2021Q2 not found on CDN
    ("JNLICNY", "2021Q1", f"{CDN}/first_quarter/jackson_ny_1q_2021_statutory_statement.pdf"),
    ("JNLICNY", "2020Q4", f"{CDN}/annual/jackson-of-ny-2020-annual-statutory-statement.pdf"),
    ("JNLICNY", "2020Q3", f"{CDN}/third_quarter/new-york-3rd-qtr-2020-statement.pdf"),
    # 2020Q2, 2020Q1 not found on CDN
]


def main():
    run_pipeline("Jackson Financial", FILINGS, PDF_DIR, TXT_DIR)


if __name__ == "__main__":
    main()
