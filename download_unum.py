"""
Download Unum Group statutory filings for two primary subsidiaries:
  FUNM - First Unum Life Insurance Company       (NY, NAIC 64297)
  ULAM - Unum Life Insurance Company of America  (ME, NAIC 62235)

Saves PDFs to companies/unum/pdfs/ and extracts text to
companies/unum/extracted/.

CDN: https://s201.q4cdn.com/630564768/files/doc_downloads/insurance-filings/
Note: Unum's CDN path structure is inconsistent across years. Known
confirmed URLs are used; inferred URLs include 404 fallback handling.
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "unum" / "pdfs"
TXT_DIR = BASE / "companies" / "unum" / "extracted"

CDN = "https://s201.q4cdn.com/630564768/files/doc_downloads/insurance-filings"

FILINGS = [
    # -- First Unum Life Insurance Company (FUNM, NY) ------------------------
    # 2023 - confirmed path pattern
    ("FUNM", "2023Q3", f"{CDN}/2023/NAIC-64297-3Q23-Quarterly-Statement-FUNM.pdf"),
    ("FUNM", "2023Q2", f"{CDN}/2023/NAIC-64297-2Q23-Quarterly-Statement-FUNM.pdf"),
    ("FUNM", "2023Q1", f"{CDN}/2023/NAIC-64297-1Q23-Quarterly-Statement-FUNM.pdf"),
    # 2022 annual amended (confirmed) + quarterly (confirmed Q1 and annual)
    ("FUNM", "2022Q4", f"{CDN}/2022/First-Unum-Life-Insurance-Company-LIFE-QS/12-31-2022/64297_38_L_2022_O_M_1_00_NA_PI.PDF"),
    ("FUNM", "2022Q3", f"{CDN}/2022/First-Unum-Life-Insurance-Company-LIFE-QS/9-30-2022/64297_38_L_2022_O_3_1_00_NA_P.PDF"),
    ("FUNM", "2022Q2", f"{CDN}/2022/First-Unum-Life-Insurance-Company-LIFE-QS/6-30-2022/64297_38_L_2022_O_2_1_00_NA_P.PDF"),
    ("FUNM", "2022Q1", f"{CDN}/2022/First-Unum-Life-Insurance-Company-LIFE-QS/64297_38_L_2022_O_1_1_00_NA_P.PDF"),
    # 2021 - confirmed Q1 and Q3
    ("FUNM", "2021Q4", f"{CDN}/2021/First-Unum-Life-Insurance-Company-LIFE-QS/12-31-2021/NAIC-64297-4Q21-Annual-Statement-FUNM.pdf"),
    ("FUNM", "2021Q3", f"{CDN}/2021/First-Unum-Life-Insurance-Company-LIFE-QS/9-30-2021/NAIC-64297-3Q21-Quarterly-Statement-FUNM.pdf"),
    ("FUNM", "2021Q2", f"{CDN}/2021/First-Unum-Life-Insurance-Company-LIFE-QS/6-30-2021/NAIC-64297-2Q21-Quarterly-Statement-FUNM.pdf"),
    ("FUNM", "2021Q1", f"{CDN}/2021/First-Unum-Life-Insurance-Company-LIFE-QS/3-31-2021/NAIC-64297-1Q21-Quarterly-Statement-FUNM.pdf"),

    # -- Unum Life Insurance Company of America (ULAM, ME) ------------------
    # 2023
    ("ULAM", "2023Q3", f"{CDN}/2023/NAIC-62235-3Q23-Quarterly-Statement-ULAM.pdf"),
    ("ULAM", "2023Q2", f"{CDN}/2023/NAIC-62235-2Q23-Quarterly-Statement-ULAM.pdf"),
    ("ULAM", "2023Q1", f"{CDN}/2023/NAIC-62235-1Q23-Quarterly-Statement-ULAM.pdf"),
    # 2022 - confirmed Q1
    ("ULAM", "2022Q4", f"{CDN}/2022/Unum-Life-Insurance-Company-of-America-LIFE-QS/12-31-2022/62235_38_L_2022_O_M_1_00_NA_PI.PDF"),
    ("ULAM", "2022Q3", f"{CDN}/2022/Unum-Life-Insurance-Company-of-America-LIFE-QS/9-30-2022/62235_38_L_2022_O_3_1_00_NA_P.PDF"),
    ("ULAM", "2022Q2", f"{CDN}/2022/Unum-Life-Insurance-Company-of-America-LIFE-QS/6-30-2022/62235_38_L_2022_O_2_1_00_NA_P.PDF"),
    ("ULAM", "2022Q1", f"{CDN}/2022/Unum-Life-Insurance-Company-of-America-LIFE-QS/62235_38_L_2022_O_1_1_00_NA_P.PDF"),
    # 2021
    ("ULAM", "2021Q4", f"{CDN}/2021/Unum-Life-Insurance-Company-of-America-LIFE-QS/12-31-2021/62235_38_L_2021_O_M_1_00_NA_PI.PDF"),
    ("ULAM", "2021Q3", f"{CDN}/2021/Unum-Life-Insurance-Company-of-America-LIFE-QS/9-30-2021/62235_38_L_2021_O_3_1_00_NA_P.PDF"),
    ("ULAM", "2021Q2", f"{CDN}/2021/Unum-Life-Insurance-Company-of-America-LIFE-QS/6-30-2021/62235_38_L_2021_O_2_1_00_NA_P.PDF"),
    ("ULAM", "2021Q1", f"{CDN}/2021/Unum-Life-Insurance-Company-of-America-LIFE-QS/3-31-2021/62235_38_L_2021_O_1_1_00_NA_P.PDF"),
]


def main():
    run_pipeline("Unum Group", FILINGS, PDF_DIR, TXT_DIR)


if __name__ == "__main__":
    main()
