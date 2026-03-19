"""
Download all AAIA (Athene Annuity and Life Company) quarterly statutory filings.
Saves PDFs to historical/pdfs/ and extracts text to historical/extracted/.
"""

import subprocess
import urllib.request
import urllib.error
from pathlib import Path

BASE = Path(__file__).resolve().parent
PDF_DIR  = BASE / "historical" / "pdfs"
TXT_DIR  = BASE / "historical" / "extracted"

PDF_DIR.mkdir(parents=True, exist_ok=True)
TXT_DIR.mkdir(parents=True, exist_ok=True)

CDN = "https://d1io3yog0oux5.cloudfront.net/_fd9b9a684a3b07e5afbf09f0754634d5/athene/db/2370"

# (period, doc_id, filename)  - AAIA only, chronological
AAIA_FILINGS = [
    # 2025
    ("2025Q4", "22531", "AAIA_4Q_2025_Statement_-_FINAL.pdf"),
    ("2025Q3", "22513", "AAIA_3Q_2025_Statement_-_FINAL.pdf"),
    ("2025Q2", "22504", "AAIA+2Q+Statement+-+FINAL.pdf"),
    ("2025Q1", "22490", "1Q+AAIA+Statement+-+FINAL.pdf"),
    # 2024
    ("2024Q4", "22482", "4Q_2024_AAIA_Statement_-_FINAL.pdf"),
    ("2024Q3", "22463", "3Q+2024+AAIA+Statement+-+FINAL.pdf"),
    ("2024Q1", "22449", "First+Quarter+2024+Statutory+Financial+Statement+for+Athene+Annuity+and+Life+Company.pdf"),
    # 2023
    ("2023Q4", "22057", "4q-2023-aaia-statement-final.pdf"),
    ("2023Q3", "22051", "third-quarter-2023-statutory-financial-statement-for-athene-annuity-and-life-company.pdf"),
    ("2023Q2", "22047", "61689-second-quarter-2023-statutory-financial-statement-for-athene-annuity-and-life-company.pdf"),
    ("2023Q1", "22043", "first-quarter-2023-statutory-financial-statement-for-athene-annuity-and-life-company.pdf"),
    # 2022
    ("2022Q4", "22039", "fourth-quarter-2022-statutory-financial-statement-for-athene-annuity-and-life-company.pdf"),
    ("2022Q3", "22035", "3Q-2022-AAIA-2-5-Notes.pdf"),
    ("2022Q2", "22031", "2Q-2022-AAIA-Statement.pdf"),
    ("2022Q1", "22027", "1Q-2022-AAIA-2-5-Notes.pdf"),
    # 2021
    ("2021Q4", "22023", "4Q-2021-AAIA-2-5-Notes.pdf"),
    ("2021Q3", "22020", "3Q-2021-AAIA-2-5-Notes.pdf"),
    ("2021Q2", "22016", "2Q-2021-AAIA-2-5-Notes.pdf"),
    ("2021Q1", "22012", "1Q-2021-AAIA-2-5-Notes.pdf"),
    # 2020
    ("2020Q4", "22008", "4Q-2020-AAIA-2-5-Notes.pdf"),
    ("2020Q3", "22004", "3Q-2020-AAIA-2-5-Notes.pdf"),
    ("2020Q2", "22000", "Second-Quarter-2020-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    ("2020Q1", "21995", "AAIA+1Q+2020+Statement+-+FINAL.pdf"),
    # 2019
    ("2019Q4", "21993", "Fourth-Quarter-2019-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    ("2019Q3", "21987", "bd18e49b-abae-0cd7-a95e-c240c4f8806b.pdf"),
    ("2019Q2", "21983", "30f338a9-396f-5175-402a-5d7bff1a8acc.pdf"),
    ("2019Q1", "21981", "2019-05-15-First-Quarter-2019-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    # 2018
    ("2018Q4", "21974", "2019-03-01-Fourth-Quarter-2018-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    ("2018Q3", "21969", "2018-11-15-Third-Quarter-2018-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    ("2018Q2", "21967", "2018-08-16-Second-Quarter-2018-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    ("2018Q1", "21963", "2018-05-17-First-Quarter-2018-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
    # 2017
    ("2017Q4", "21958", "2018-03-01-Fourth-Quarter-2017-Statutory-Financial-Statement-for-Athene-Annuity-and-Life-Company-%28Unaudited%29.pdf"),
]


def download(period: str, doc_id: str, remote_filename: str) -> Path | None:
    url = f"{CDN}/{doc_id}/pdf/{remote_filename}"
    local_pdf = PDF_DIR / f"AAIA_{period}.pdf"

    if local_pdf.exists():
        print(f"  [skip] {period} already downloaded")
        return local_pdf

    print(f"  Downloading {period}...", end=" ", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            local_pdf.write_bytes(resp.read())
        size_mb = local_pdf.stat().st_size / 1e6
        print(f"OK ({size_mb:.1f} MB)")
        return local_pdf
    except Exception as e:
        print(f"FAILED: {e}")
        return None


def extract_text(period: str, pdf_path: Path) -> Path | None:
    txt_path = TXT_DIR / f"AAIA_{period}.txt"
    if txt_path.exists():
        print(f"  [skip] {period} text already extracted")
        return txt_path

    print(f"  Extracting text {period}...", end=" ", flush=True)
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        lines = len(txt_path.read_text(encoding="utf-8", errors="ignore").splitlines())
        print(f"OK ({lines:,} lines)")
        return txt_path
    else:
        print(f"FAILED: {result.stderr[:100]}")
        return None


def main():
    print(f"Downloading {len(AAIA_FILINGS)} AAIA quarterly filings...\n")
    ok_pdf = 0
    ok_txt = 0
    for period, doc_id, filename in AAIA_FILINGS:
        pdf = download(period, doc_id, filename)
        if pdf:
            ok_pdf += 1
            txt = extract_text(period, pdf)
            if txt:
                ok_txt += 1

    print(f"\nDone: {ok_pdf}/{len(AAIA_FILINGS)} PDFs, {ok_txt}/{len(AAIA_FILINGS)} text files")


if __name__ == "__main__":
    main()
