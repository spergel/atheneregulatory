"""
Shared utilities for NAIC statutory filing download pipelines.

Provides download(), extract_text(), and run_pipeline() used by all
company-specific download scripts.
"""

import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


def download(
    entity: str,
    period: str,
    url: str,
    pdf_dir: Path,
    timeout: int = 120,
) -> Path | None:
    local_pdf = pdf_dir / f"{entity}_{period}.pdf"
    if local_pdf.exists():
        print(f"  [skip] {entity} {period}")
        return local_pdf
    print(f"  Downloading {entity} {period}...", end=" ", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            with local_pdf.open("wb") as f:
                shutil.copyfileobj(resp, f)
        print(f"OK ({local_pdf.stat().st_size / 1e6:.1f} MB)")
        return local_pdf
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} - skipping")
        return None
    except Exception as e:
        print(f"FAILED: {e}")
        return None


def extract_text(
    entity: str,
    period: str,
    pdf_path: Path,
    txt_dir: Path,
) -> Path | None:
    txt_path = txt_dir / f"{entity}_{period}.txt"
    if txt_path.exists():
        print(f"  [skip] {entity} {period} text")
        return txt_path
    print(f"  Extracting {entity} {period}...", end=" ", flush=True)
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        lines = len(txt_path.read_text(encoding="utf-8", errors="ignore").splitlines())
        print(f"OK ({lines:,} lines)")
        return txt_path
    print(f"FAILED: {result.stderr[:120]}")
    return None


def run_pipeline(
    company: str,
    filings: list[tuple[str, str, str]],
    pdf_dir: Path,
    txt_dir: Path,
    timeout: int = 120,
    note: str = "",
) -> None:
    """Download and extract text for a list of (entity, period, url) filings."""
    pdf_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)

    by_entity: dict[str, list[tuple[str, str]]] = {}
    for entity, period, url in filings:
        by_entity.setdefault(entity, []).append((period, url))
    entities = sorted(by_entity)

    entity_word = "entity" if len(entities) == 1 else "entities"
    print(f"{company} - {len(filings)} filings across {len(entities)} {entity_word}\n")
    if note:
        print(f"Note: {note}\n")

    for entity in entities:
        subset = by_entity[entity]
        print(f"-- {entity} ({len(subset)} filings) --")
        for period, url in subset:
            pdf = download(entity, period, url, pdf_dir, timeout)
            if pdf:
                extract_text(entity, period, pdf, txt_dir)
        print()

    total_pdf = sum(1 for _ in pdf_dir.glob("*.pdf"))
    total_txt = sum(1 for _ in txt_dir.glob("*.txt"))
    company_dir = pdf_dir.parent.name
    print(f"Done: {total_pdf} PDFs, {total_txt} text files in companies/{company_dir}/")
