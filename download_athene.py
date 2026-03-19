"""
Download Athene statutory filings:
  AAIA - Athene Annuity and Life Company (IA, NAIC 61689)

Saves PDFs to companies/athene/pdfs/ and extracts text to
companies/athene/extracted/.

CDN: https://d1io3yog0oux5.cloudfront.net/_fd9b9a684a3b07e5afbf09f0754634d5/athene/db/2370
URL pattern: {CDN}/{doc_id}/pdf/{filename}

Note: Athene Holding was taken private by Apollo Global Management in
January 2022 but continues to post statutory filings on their IR CDN.
Coverage: 2017Q4–2025Q4.
"""

from pathlib import Path

from lib.statutory_pipeline import run_pipeline

BASE    = Path(__file__).resolve().parent
PDF_DIR = BASE / "companies" / "athene" / "pdfs"
TXT_DIR = BASE / "companies" / "athene" / "extracted"

CDN = "https://d1io3yog0oux5.cloudfront.net/_fd9b9a684a3b07e5afbf09f0754634d5/athene/db/2370"

# (entity, period, doc_id, filename)
_RAW = [
    # 2025
    ("AAIA", "2025Q4", "22531", "AAIA_4Q_2025_Statement_-_FINAL.pdf"),
    ("AAIA", "2025Q3", "22513", "AAIA_3Q_2025_Statement_-_FINAL.pdf"),
    ("AAIA", "2025Q2", "22504", "AAIA+2Q+Statement+-+FINAL.pdf"),
    ("AAIA", "2025Q1", "22490", "1Q+AAIA+Statement+-+FINAL.pdf"),
    # 2024
    ("AAIA", "2024Q4", "22482", "4Q_2024_AAIA_Statement_-_FINAL.pdf"),
    ("AAIA", "2024Q3", "22463", "3Q+2024+AAIA+Statement+-+FINAL.pdf"),
    ("AAIA", "2024Q1", "22449", "First+Quarter+2024+Statutory+Financial+Statement+for+Athene+Annuity+and+Life+Company.pdf"),
    # 2023
    ("AAIA", "2023Q4", "22057", "4q-2023-aaia-statement-final.pdf"),
    ("AAIA", "2023Q3", "22051", "third-quarter-2023-statutory-financial-statement-for-athene-annuity-and-life-company.pdf"),
    ("AAIA", "2023Q2", "22047", "61689-second-quarter-2023-statutory-financial-statement-for-athene-annuity-and-life-company.pdf"),
    ("AAIA", "2023Q1", "22043", "first-quarter-2023-statutory-financial-statement-for-athene-annuity-and-life-company.pdf"),
    # 2022
    ("AAIA", "2022Q4", "22039", "fourth-quarter-2022-statutory-financial-statement-for-athene-annuity-and-life-company.pdf"),
    ("AAIA", "2022Q3", "22035", "3Q-2022-AAIA-2-5-Notes.pdf"),
    ("AAIA", "2022Q2", "22031", "2Q-2022-AAIA-Statement.pdf"),
    ("AAIA", "2022Q1", "22027", "1Q-2022-AAIA-2-5-Notes.pdf"),
    # 2021
    ("AAIA", "2021Q4", "22023", "4Q-2021-AAIA-2-5-Notes.pdf"),
    ("AAIA", "2021Q3", "22020", "3Q-2021-AAIA-2-5-Notes.pdf"),
    ("AAIA", "2021Q2", "22016", "2Q-2021-AAIA-2-5-Notes.pdf"),
    ("AAIA", "2021Q1", "22012", "1Q-2021-AAIA-2-5-Notes.pdf"),
    # 2020
    ("AAIA", "2020Q4", "22008", "4Q-2020-AAIA-2-5-Notes.pdf"),
    ("AAIA", "2020Q3", "22004", "3Q-2020-AAIA-2-5-Notes.pdf"),
    ("AAIA", "2020Q2", "22000", "Second-Quarter-2020-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    ("AAIA", "2020Q1", "21995", "AAIA+1Q+2020+Statement+-+FINAL.pdf"),
    # 2019
    ("AAIA", "2019Q4", "21993", "Fourth-Quarter-2019-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    ("AAIA", "2019Q3", "21987", "bd18e49b-abae-0cd7-a95e-c240c4f8806b.pdf"),
    ("AAIA", "2019Q2", "21983", "30f338a9-396f-5175-402a-5d7bff1a8acc.pdf"),
    ("AAIA", "2019Q1", "21981", "2019-05-15-First-Quarter-2019-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    # 2018
    ("AAIA", "2018Q4", "21974", "2019-03-01-Fourth-Quarter-2018-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    ("AAIA", "2018Q3", "21969", "2018-11-15-Third-Quarter-2018-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    ("AAIA", "2018Q2", "21967", "2018-08-16-Second-Quarter-2018-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    ("AAIA", "2018Q1", "21963", "2018-05-17-First-Quarter-2018-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    # 2017
    ("AAIA", "2017Q4", "21958", "2018-03-01-Fourth-Quarter-2017-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
]

FILINGS = [(entity, period, f"{CDN}/{doc_id}/pdf/{filename}")
           for entity, period, doc_id, filename in _RAW]


def main():
    run_pipeline("Athene", FILINGS, PDF_DIR, TXT_DIR)


if __name__ == "__main__":
    main()
