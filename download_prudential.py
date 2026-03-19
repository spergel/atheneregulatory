"""
Download Prudential Financial statutory filings:
  PICA - The Prudential Insurance Company of America (NJ, NAIC 68241)

Saves PDFs to companies/prudential/pdfs/ and extracts text to
companies/prudential/extracted/.

CDN: https://s203.q4cdn.com/245412310/files/
Note: Prudential publishes "STAT Summaries" - condensed statutory
financial statements prepared per NAIC SAP. They contain the same
schedule structure as full filings and parse identically.
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "prudential" / "pdfs"
TXT_DIR = BASE / "companies" / "prudential" / "extracted"

CDN = "https://s203.q4cdn.com/245412310/files"

FILINGS = [
    # -- Prudential Insurance Company of America (PICA) ----------------------
    # 2025 - doc_financials path
    ("PICA", "2025Q3", f"{CDN}/doc_financials/2025/q3/3Q25-PICA-STAT-Summary.pdf"),
    ("PICA", "2025Q2", f"{CDN}/doc_financials/2025/q2/2Q25-PICA-STAT-Summary.pdf"),
    ("PICA", "2025Q1", f"{CDN}/doc_financials/2025/q1/1Q25-PICA-STAT-Summary.pdf"),
    # 2024 - doc_financials path (inferred from 2025 pattern)
    ("PICA", "2024Q4", f"{CDN}/doc_financials/2024/q4/4Q24-PICA-STAT-Summary.pdf"),
    ("PICA", "2024Q3", f"{CDN}/doc_financials/2024/q3/3Q24-PICA-STAT-Summary.pdf"),
    ("PICA", "2024Q2", f"{CDN}/doc_financials/2024/q2/2Q24-PICA-STAT-Summary.pdf"),
    ("PICA", "2024Q1", f"{CDN}/doc_financials/2024/q1/1Q24-PICA-STAT-Summary.pdf"),
    # 2023 - quarterly_statements path (confirmed Q2)
    ("PICA", "2023Q4", f"{CDN}/quarterly_statements/2023_4Q-PICA-STAT-Summary.pdf"),
    ("PICA", "2023Q3", f"{CDN}/quarterly_statements/2023_3Q-PICA-STAT-Summary.pdf"),
    ("PICA", "2023Q2", f"{CDN}/quarterly_statements/2023_2Q-PICA-STAT-Summary.pdf"),
    ("PICA", "2023Q1", f"{CDN}/quarterly_statements/2023_1Q-PICA-STAT-Summary.pdf"),
    # 2022 - quarterly_statements path (confirmed Q2)
    ("PICA", "2022Q4", f"{CDN}/quarterly_statements/2022_4Q-PICA-STAT-Summary.pdf"),
    ("PICA", "2022Q3", f"{CDN}/quarterly_statements/2022_3Q-PICA-STAT-Summary.pdf"),
    ("PICA", "2022Q2", f"{CDN}/quarterly_statements/2022_2Q-PICA-STAT-Summary.pdf"),
    ("PICA", "2022Q1", f"{CDN}/quarterly_statements/2022_1Q-PICA-STAT-Summary.pdf"),
    # 2021
    ("PICA", "2021Q4", f"{CDN}/quarterly_statements/2021_4Q-PICA-STAT-Summary.pdf"),
    ("PICA", "2021Q3", f"{CDN}/quarterly_statements/2021_3Q-PICA-STAT-Summary.pdf"),
    ("PICA", "2021Q2", f"{CDN}/quarterly_statements/2021_2Q-PICA-STAT-Summary.pdf"),
    ("PICA", "2021Q1", f"{CDN}/quarterly_statements/2021_1Q-PICA-STAT-Summary.pdf"),
]


def main():
    run_pipeline("Prudential Financial", FILINGS, PDF_DIR, TXT_DIR)


if __name__ == "__main__":
    main()
