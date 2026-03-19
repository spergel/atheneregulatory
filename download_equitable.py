"""
Download Equitable Holdings statutory filings for two subsidiaries:
  EFLIC - Equitable Financial Life Insurance Company      (NY, NAIC 62944)
  EFLOA - Equitable Financial Life Insurance Company of America (AZ, NAIC 78077)

Saves PDFs to companies/equitable/pdfs/ and extracts text to
companies/equitable/extracted/.

CDN: https://s24.q4cdn.com/845726123/files/doc_downloads/
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "equitable" / "pdfs"
TXT_DIR = BASE / "companies" / "equitable" / "extracted"

CDN = "https://s24.q4cdn.com/845726123/files/doc_downloads"

FILINGS = [
    # -- Equitable Financial Life Insurance Company (EFLIC, NY) ------------
    ("EFLIC", "2025Q1", f"{CDN}/statutory/2025/06/Q1-2025-EFLIC-Quarterly-Statement.pdf"),
    ("EFLIC", "2024Q4", f"{CDN}/statutory/2025/03/EFLIC-Annual-Statement-2024.pdf"),
    ("EFLIC", "2024Q3", f"{CDN}/statutory/2024/11/EFLIC-Q3-2024-Statutory-Statement.pdf"),
    ("EFLIC", "2024Q2", f"{CDN}/statutory/2024/08/EFLIC-Q2-2024-Statutory-Statement.pdf"),
    ("EFLIC", "2024Q1", f"{CDN}/statutory/2024/05/EFLIC-Q1-2024-Statutory-Statement.pdf"),
    ("EFLIC", "2023Q4", f"{CDN}/statutory/2024/03/EFLIC-Annual-Statement-2023.pdf"),
    ("EFLIC", "2023Q3", f"{CDN}/statutory/2023/09/eflic-q3-2023-statutory-statement.pdf"),
    ("EFLIC", "2023Q2", f"{CDN}/statutory/2023/06/EFLIC-Q2-2023-Quarterly-Statement.pdf"),
    ("EFLIC", "2023Q1", f"{CDN}/statutory/2023/03/EFLIC-1Q-2023-Quarterly-Statement.pdf"),
    ("EFLIC", "2022Q4", f"{CDN}/statutory/2023/03/EFLIC-Annual-Statement-2022.pdf"),
    ("EFLIC", "2022Q3", f"{CDN}/statutory/2022/11/EFLIC-Q3-2022-Statutory-Statement.pdf"),
    ("EFLIC", "2022Q2", f"{CDN}/statutory/2022/08/EFLIC-Q2-2022-Statutory-Statement.pdf"),
    ("EFLIC", "2022Q1", f"{CDN}/statutory/2022/05/EFLIC-Q1-2022-Statutory-Statement.pdf"),
    ("EFLIC", "2021Q4", f"{CDN}/statutory/2022/03/EFLIC-Annual-Statement-2021.pdf"),
    ("EFLIC", "2021Q3", f"{CDN}/statutory/2021/11/EFLIC-Q3-2021-Statutory-Statement.pdf"),
    ("EFLIC", "2021Q2", f"{CDN}/statutory/2021/08/EFLIC-Q2-2021-Statutory-Statement.pdf"),
    ("EFLIC", "2021Q1", f"{CDN}/statutory/2021/05/EFLIC-Q1-2021-Statutory-Statement.pdf"),
    ("EFLIC", "2020Q4", f"{CDN}/statutory/2021/03/EFLIC-Annual-Statement-2020.pdf"),
    ("EFLIC", "2020Q3", f"{CDN}/statutory/2020/11/EFLIC-Q3-2020-Statutory-Statement.pdf"),
    ("EFLIC", "2020Q2", f"{CDN}/statutory/2020/08/EFLIC-Q2-2020-Statutory-Statement.pdf"),

    # -- Equitable Financial Life Insurance Company of America (EFLOA, AZ) --
    ("EFLOA", "2025Q1", f"{CDN}/statutory/2025/06/Q1-2025-EFLOA-Quarterly-Statement.pdf"),
    ("EFLOA", "2024Q4", f"{CDN}/statutory/2025/03/EFLOA-Annual-Statement-2024.pdf"),
    ("EFLOA", "2024Q3", f"{CDN}/2024/EFLOA-Q3-2024-Statutory-Statement.pdf"),
    ("EFLOA", "2024Q2", f"{CDN}/statutory/2024/08/EFLOA-Q2-2024-Statutory-Statement.pdf"),
    ("EFLOA", "2024Q1", f"{CDN}/statutory/2024/05/EFLOA-Q1-2024-Statutory-Statement.pdf"),
    ("EFLOA", "2023Q4", f"{CDN}/statutory/2024/03/EFLOA-Annual-Statement-2023.pdf"),
    ("EFLOA", "2023Q3", f"{CDN}/statutory/2023/11/EFLOA-Q3-2023-Statutory-Statement.pdf"),
    ("EFLOA", "2023Q2", f"{CDN}/statutory/2023/08/EFLOA-Q2-2023-Statutory-Statement.pdf"),
    ("EFLOA", "2023Q1", f"{CDN}/statutory/2023/05/EFLOA-Q1-2023-Statutory-Statement.pdf"),
    ("EFLOA", "2022Q4", f"{CDN}/2022/12/EFLOA-Annual-2022-Statement.pdf"),
    ("EFLOA", "2022Q3", f"{CDN}/statutory/2022/11/EFLOA-Q3-2022-Statutory-Statement.pdf"),
    ("EFLOA", "2022Q2", f"{CDN}/statutory/2022/08/EFLOA-Q2-2022-Statutory-Statement.pdf"),
    ("EFLOA", "2022Q1", f"{CDN}/statutory/2022/05/EFLOA-Q1-2022-Statutory-Statement.pdf"),
    ("EFLOA", "2021Q4", f"{CDN}/statutory/2022/03/EFLOA-Annual-Statement-2021.pdf"),
    ("EFLOA", "2021Q1", f"{CDN}/statutory/2021/05/EFLOA-1st-Qtr-2021-78077.pdf"),
    ("EFLOA", "2020Q2", f"{CDN}/statutory/2020/08/Equitable-Financial-Life-Insurance-Company-of-America-Second-Quarter-Statement-2020.pdf"),
]


def main():
    run_pipeline("Equitable Holdings", FILINGS, PDF_DIR, TXT_DIR)


if __name__ == "__main__":
    main()
