"""
Download MetLife statutory filings for two primary subsidiaries:
  MLIC - Metropolitan Life Insurance Company   (NY, NAIC 65978)
  MTL  - Metropolitan Tower Life Insurance Company (NE, NAIC 97136)

Saves PDFs to companies/metlife/pdfs/ and extracts text to
companies/metlife/extracted/.

CDN: https://s201.q4cdn.com/280976757/files/doc_downloads/
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "metlife" / "pdfs"
TXT_DIR = BASE / "companies" / "metlife" / "extracted"

CDN = "https://s201.q4cdn.com/280976757/files/doc_downloads"

FILINGS = [
    # -- Metropolitan Life Insurance Company (MLIC) --------------------------
    ("MLIC", "2025Q3", f"{CDN}/statutory-filings/metropolitan/2025/MLIC-Q3-2025-Final-Statement.pdf"),
    ("MLIC", "2025Q2", f"{CDN}/statutory-filings/metropolitan/2025/MLIC-Q2-2025-Final-Statement.pdf"),
    ("MLIC", "2025Q1", f"{CDN}/statutory-filings/metropolitan/2025/MLIC-Q1-2025-Final-Statement.pdf"),
    ("MLIC", "2024Q4", f"{CDN}/statutory-filings/metropolitan/2024/mlic-annual-2024-final-statement.pdf"),
    ("MLIC", "2024Q3", f"{CDN}/statutory-filings/MLIC-Q3-2024-Final-Statement.pdf"),
    ("MLIC", "2024Q2", f"{CDN}/statutory-filings/metropolitan/2024/mlic-q2-2024-final-statement.pdf"),
    ("MLIC", "2024Q1", f"{CDN}/statutory-filings/metropolitan/2024/mlic-q1-2024-final-statement.pdf"),
    ("MLIC", "2023Q4", f"{CDN}/statutory-filings/metropolitan/2023/mlic-annual-2023-final-statement.pdf"),
    ("MLIC", "2023Q3", f"{CDN}/statutory-filings/metropolitan/2023/11/q3-2023-mlic-quarterly-statement.pdf"),
    ("MLIC", "2023Q2", f"{CDN}/statutory-filings/metropolitan/2023/mlic-q2-2023-final-statement.pdf"),
    ("MLIC", "2023Q1", f"{CDN}/2023/MLIC-Q1-2023-Final.pdf"),
    ("MLIC", "2022Q4", f"{CDN}/statutory-filings/metropolitan/2022/mlic-annual-2022-final-statement.pdf"),
    ("MLIC", "2022Q3", f"{CDN}/statutory-filings/metropolitan/2022/mlic-q3-2022-final-statement.pdf"),
    ("MLIC", "2022Q2", f"{CDN}/statutory-filings/metropolitan/2022/mlic-q2-2022-final-statement.pdf"),
    ("MLIC", "2022Q1", f"{CDN}/statutory-filings/metropolitan/2022/mlic-q1-2022-final-statement.pdf"),

    # -- Metropolitan Tower Life Insurance Company (MTL) --------------------
    ("MTL", "2025Q3", f"{CDN}/statutory-filings/metropolitan-tower/2025/MTL-Q3-2025-Final-Statement.pdf"),
    ("MTL", "2025Q2", f"{CDN}/statutory-filings/metropolitan-tower/2025/MTL-Q2-2025-Final-Statement.pdf"),
    ("MTL", "2025Q1", f"{CDN}/statutory-filings/metropolitan-tower/2025/MTL-Q1-2025-Final-Statement.pdf"),
    ("MTL", "2024Q4", f"{CDN}/statutory-filings/metropolitan-tower/2024/2024-mtl-annual-statement.pdf"),
    ("MTL", "2024Q3", f"{CDN}/statutory-filings/MTL-Q3-2024-Final-Statement.pdf"),
    ("MTL", "2024Q2", f"{CDN}/statutory-filings/metropolitan-tower/2024/mtl-q2-2024-final-statement.pdf"),
    ("MTL", "2024Q1", f"{CDN}/statutory-filings/metropolitan-tower/2024/mtl-q1-2024-final-statement.pdf"),
    ("MTL", "2023Q4", f"{CDN}/statutory-filings/metropolitan-tower/2023/2023-mtl-annual-statement.pdf"),
    ("MTL", "2023Q3", f"{CDN}/statutory-filings/metropolitan-tower/2023/11/q3-2023-mtl-quarterly-statement.pdf"),
    ("MTL", "2023Q2", f"{CDN}/statutory-filings/metropolitan-tower/2023/mtl-q2-2023-final-statement.pdf"),
    ("MTL", "2023Q1", f"{CDN}/statutory-filings/metropolitan-tower/2023/mtl-q1-2023-final-statement.pdf"),
    ("MTL", "2022Q4", f"{CDN}/statutory-filings/metropolitan-tower/2022/2022-mtl-annual-statement.pdf"),
    ("MTL", "2022Q3", f"{CDN}/statutory-filings/metropolitan-tower/2022/mtl-q3-2022-final-statement.pdf"),
    ("MTL", "2022Q2", f"{CDN}/statutory-filings/metropolitan-tower/2022/mtl-q2-2022-final-statement.pdf"),
    ("MTL", "2022Q1", f"{CDN}/statutory-filings/metropolitan-tower/2022/mtl-q1-2022-final-statement.pdf"),
]


def main():
    run_pipeline("MetLife", FILINGS, PDF_DIR, TXT_DIR)


if __name__ == "__main__":
    main()
