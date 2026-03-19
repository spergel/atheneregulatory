"""
Download Voya Financial statutory filings:
  VRIAC - Voya Retirement Insurance and Annuity Company (CT, NAIC 86509)

Saves PDFs to companies/voya/pdfs/ and extracts text to
companies/voya/extracted/.

CDN: https://s21.q4cdn.com/836187199/files/doc_downloads/
Note: Voya's CDN path structure varies by year - URLs confirmed from
search results where available, pattern-inferred elsewhere.
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "voya" / "pdfs"
TXT_DIR = BASE / "companies" / "voya" / "extracted"

CDN = "https://s21.q4cdn.com/836187199/files/doc_downloads"

FILINGS = [
    # -- Voya Retirement Insurance and Annuity Company (VRIAC) ---------------
    # 2025 (confirmed Q1, Q2)
    ("VRIAC", "2025Q2", f"{CDN}/2025/08/VRIAC_2Q25.pdf"),
    ("VRIAC", "2025Q1", f"{CDN}/voya_download_list/2025/05/VOYA-RETIREMENT-INSURANCE-AND-ANNUITY-COMPANY-1Q-25.pdf"),
    # 2024 (confirmed Q2, Q3; Q4 inferred from Voya labeling pattern)
    ("VRIAC", "2024Q4", f"{CDN}/2025/03/vriac_4q24_statement_final.pdf"),
    ("VRIAC", "2024Q3", f"{CDN}/2024/11/VRIAC_3Q24_Statement_Final.pdf"),
    ("VRIAC", "2024Q2", f"{CDN}/voya_download_list/2024/vriac_2q24_statement_final.pdf"),
    ("VRIAC", "2024Q1", f"{CDN}/voya_download_list/2024/vriac_1q24_statement_final.pdf"),
    # 2023 (confirmed Q2 and Q4; rest inferred)
    ("VRIAC", "2023Q4", f"{CDN}/2024/vriac_4q23_bb_final.pdf"),
    ("VRIAC", "2023Q3", f"{CDN}/2023/VOYA-RETIREMENT-INSURANCE-AND-ANNUITY-COMPANY-3RD-QUARTER-FINANCIALS-2023.pdf"),
    ("VRIAC", "2023Q2", f"{CDN}/2023/VOYA-RETIREMENT-INSURANCE-AND-ANNUITY-COMPANY-2ND-QUARTER-FINANCIALS-2023.pdf"),
    ("VRIAC", "2023Q1", f"{CDN}/2023/VOYA-RETIREMENT-INSURANCE-AND-ANNUITY-COMPANY-1ST-QUARTER-FINANCIALS-2023.pdf"),
    # 2022 (inferred)
    ("VRIAC", "2022Q4", f"{CDN}/voya_download_list/2023/vriac_4q22_statement_final.pdf"),
    ("VRIAC", "2022Q3", f"{CDN}/voya_download_list/2022/vriac_3q22_statement_final.pdf"),
    ("VRIAC", "2022Q2", f"{CDN}/voya_download_list/2022/vriac_2q22_statement_final.pdf"),
    ("VRIAC", "2022Q1", f"{CDN}/voya_download_list/2022/vriac_1q22_statement_final.pdf"),
    # 2021 annual (confirmed label says "2020" but is the 2021 statement filed in 2021/03)
    ("VRIAC", "2021Q4", f"{CDN}/2021/03/Voya-Retirement-Insurance-and-Annuity-Company-Annual-Statement-2021.PDF"),
    ("VRIAC", "2021Q3", f"{CDN}/voya_download_list/2021/vriac_3q21_statement_final.pdf"),
    ("VRIAC", "2021Q2", f"{CDN}/voya_download_list/2021/vriac_2q21_statement_final.pdf"),
    ("VRIAC", "2021Q1", f"{CDN}/voya_download_list/2021/vriac_1q21_statement_final.pdf"),
    # Historical
    ("VRIAC", "2019Q3", f"{CDN}/voya_download_list/Voya-Retirement-Insurance-and-Annuity-Company-Quarterly-Statement-3Q19.pdf"),
]


def main():
    run_pipeline("Voya Financial", FILINGS, PDF_DIR, TXT_DIR)


if __name__ == "__main__":
    main()
