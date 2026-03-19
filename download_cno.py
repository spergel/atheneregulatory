"""
Download CNO Financial statutory filings for two subsidiaries:
  BLC  - Bankers Life and Casualty Company    (IL, NAIC 61263)
  CPL  - Colonial Penn Life Insurance Company (PA, NAIC 62065)

Saves PDFs to companies/cno/pdfs/ and extracts text to
companies/cno/extracted/.

CDN: https://s28.q4cdn.com/966891126/files/doc_financials/
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "cno" / "pdfs"
TXT_DIR = BASE / "companies" / "cno" / "extracted"

CDN = "https://s28.q4cdn.com/966891126/files/doc_financials"

FILINGS = [
    # -- Bankers Life and Casualty Company (BLC) ----------------------------
    # 2024 - confirmed annual and Q3
    ("BLC", "2024Q4", f"{CDN}/2024/q4/Bankers-Life-Casualty-Company-NAIC-61263-Annual-Statement-2024-final.pdf"),
    ("BLC", "2024Q3", f"{CDN}/2024/q3/61263_38_L_2024_O_3_1_00_NA_P.pdf"),
    ("BLC", "2024Q2", f"{CDN}/2024/q2/61263_38_L_2024_O_2_1_00_NA_P.pdf"),
    ("BLC", "2024Q1", f"{CDN}/2024/q1/61263_38_L_2024_O_1_1_00_NA_P.pdf"),
    # 2023 - confirmed Q3 and annual
    ("BLC", "2023Q4", f"{CDN}/2023/q4/Bankers-Life-and-Casualty-NAIC-61263-Annual-Statement-2023.pdf"),
    ("BLC", "2023Q3", f"{CDN}/2023/q3/11/Bankers-Life-and-Casualty-NAIC-61263-3Q23.pdf"),
    ("BLC", "2023Q2", f"{CDN}/2023/q2/Bankers-Life-and-Casualty-NAIC-61263-2Q23.pdf"),
    ("BLC", "2023Q1", f"{CDN}/2023/q1/Bankers-Life-and-Casualty-NAIC-61263-1Q23.pdf"),
    # 2022 - confirmed annual and Q1
    ("BLC", "2022Q4", f"{CDN}/2022/q4/bankers-life-casualty-company-naic-61263-annual-statement.pdf"),
    ("BLC", "2022Q3", f"{CDN}/2022/q3/Bankers-Life-and-Casualty-NAIC-61263-3Q22.pdf"),
    ("BLC", "2022Q2", f"{CDN}/2022/q2/Bankers-Life-and-Casualty-NAIC-61263-2Q22.pdf"),
    ("BLC", "2022Q1", f"{CDN}/2022/q1/1Q22-BLC-Print-Statement.pdf"),
    # 2021 - confirmed Q2
    ("BLC", "2021Q4", f"{CDN}/2021/q4/BLC-Annual-Statement.pdf"),
    ("BLC", "2021Q3", f"{CDN}/2021/q3/BLC-3Q21-Statement.pdf"),
    ("BLC", "2021Q2", f"{CDN}/2021/q2/BLC-2Q21-Statement.pdf"),
    ("BLC", "2021Q1", f"{CDN}/2021/q1/BLC-1Q21-Statement.pdf"),
    # 2020
    ("BLC", "2020Q4", f"{CDN}/2020/q4/BLC-Annual-Statement.pdf"),
    ("BLC", "2020Q3", f"{CDN}/2020/q3/BLC-3Q20-Statement.pdf"),
    ("BLC", "2020Q2", f"{CDN}/2020/q2/BLC-2Q20-Statement.pdf"),
    ("BLC", "2020Q1", f"{CDN}/2020/q1/BLC-1Q20-Statement.pdf"),
    # Historical confirmed
    ("BLC", "2019Q2", f"{CDN}/2019/q2/BLC-2Q19-Printed-Statement.pdf"),
    ("BLC", "2018Q3", f"{CDN}/2018/q3/BLC-Printed-Statement.pdf"),

    # -- Colonial Penn Life Insurance Company (CPL) --------------------------
    # 2023 - confirmed annual
    ("CPL", "2023Q4", f"{CDN}/2023/q4/Colonial-Penn-Life-Insurance-Company-NAIC-62065-2023-Annual-Statement.pdf"),
    ("CPL", "2023Q3", f"{CDN}/2023/q3/Colonial-Penn-Life-Insurance-Company-NAIC-62065-3Q23.pdf"),
    ("CPL", "2022Q4", f"{CDN}/2022/q4/Colonial-Penn-Life-Insurance-Company-NAIC-62065-Annual-Statement-2022.pdf"),
    ("CPL", "2022Q3", f"{CDN}/2022/q3/Colonial-Penn-Life-Insurance-Company-NAIC-62065-3Q22.pdf"),
    ("CPL", "2021Q4", f"{CDN}/2021/q4/Colonial-Penn-Life-Insurance-Company-Annual-Statement.pdf"),
    ("CPL", "2021Q3", f"{CDN}/2021/q3/Colonial-Penn-Life-Insurance-Company-3Q21.pdf"),
]


def main():
    run_pipeline("CNO Financial", FILINGS, PDF_DIR, TXT_DIR)


if __name__ == "__main__":
    main()
