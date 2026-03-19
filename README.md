# NAIC Statutory Filings Dashboard

A pipeline that downloads statutory financial filings (PDFs) from insurance company IR sites, parses NAIC schedules, and serves a static dashboard via Vercel.

## Companies Covered

| Company | Ticker | Entities | NAIC IDs | Coverage | Frequency |
|---------|--------|----------|----------|----------|-----------|
| Athene | ATH | AAIA | 61689 | 2017–2025 | Quarterly |
| Brighthouse Financial | BHF | BLIC, NELIC, BLICNY | 68030, 91838, 73329 | 2016–2025 | Quarterly |
| Jackson Financial | JXN | JNLIC, JNLICNY | 65056, 65080 | 2020–2025 | Quarterly (gaps 2021–22) |
| Lincoln National | LNC | LNL, LLANY | 65676, 60038 | 2019–2023 | Annual only |
| MetLife | MET | MLIC, MTL | 65978, 97136 | 2022–2025 | Quarterly (some gaps) |
| Prudential Financial | PRU | PICA | 68241 | 2021–2025 | Quarterly |
| Corebridge Financial | CRBG | AGL, VALIC, USL | 60488, 70238, 70106 | 2021–2025 | Annual only |
| Principal Financial | PFG | PLIC | 61271 | 2025 only | Quarterly |
| Voya Financial | VOYA | VRIAC | 86509 | 2019–2025 | Quarterly (gaps 2020–22) |
| Unum Group | UNM | FUNM, ULAM | 62235, 62491 | 2021–2023 | Sparse |
| Equitable Holdings | EQH | EFLIC, EFLOA | 62944, 62952 | 2020–2025 | Sparse |
| CNO Financial | CNO | BLC, CPL | 61271, 20214 | 2018–2024 | Sparse |

### Known Gaps

- **MetLife 2022–2023**: Most filings were removed from MetLife's CDN; confirmed 404s.
- **Prudential Q4 annuals**: Only quarterly STAT Summaries are posted publicly; no separate Q4 annual filing.
- **Voya 2020–2022**: CDN URL patterns inferred; several periods confirmed 404.
- **Unum / Equitable / CNO**: Sparse and irregular; IR sites do not post a consistent quarterly schedule.
- **Principal 2022–2024**: Uses opaque UUIDs; 2022–2024 UUIDs must be extracted manually from `investors.principal.com/financials/statutory-filings`.
- **Lincoln 2024+**: 2024 annual not yet confirmed on IR site.
- **Athene 2024Q2**: Q2 2024 not listed in the CDN index (gap between 2024Q1 and 2024Q3).

---

## Pipeline

Each step reads from the previous step's output.

```
download_<company>.py
  └── companies/<company>/pdfs/

extract_schedules.py
  └── companies/<company>/schedules/

extract_kpis.py
  └── companies/<company>/  (timeseries JSON + CSV)

build_web_data.py
  └── website/data/          (JSON + CSV for dashboard)
```

### 1. Download PDFs

Run any download script individually:

```bash
python download_athene.py
python download_brighthouse.py
python download_jackson.py
python download_lincoln.py
python download_metlife.py
python download_prudential.py
python download_corebridge.py
python download_principal.py
python download_voya.py
python download_unum.py
python download_equitable.py
python download_cno.py
```

PDFs are saved to `companies/<company>/pdfs/` and text is extracted to `companies/<company>/extracted/`. The pipeline skips files already on disk.

### 2. Extract Schedules

Parse the extracted text into per-schedule CSVs:

```bash
python extract_schedules.py
```

Outputs one CSV per schedule per filing period, e.g.:
- `BLIC_2024Q3_sched_t.csv` — Schedule T (premiums by state)
- `BLIC_2024Q3_sched_d_quality.csv` — Schedule D quality breakdown
- `BLIC_2024Q3_sched_b.csv` — Schedule B (mortgage loans)
- `BLIC_2024Q3_sched_ba.csv` — Schedule BA (other long-term assets)

### 3. Extract KPIs

Aggregate into per-entity timeseries:

```bash
python extract_kpis.py
```

Outputs:
- `companies/<company>/<ENTITY>_timeseries.json` — period-by-period KPIs
- `companies/<company>/all_timeseries.json` — all entities combined

### 4. Build Web Data

Compile everything into static JSON/CSV for the dashboard:

```bash
python build_web_data.py
```

Outputs to `website/data/`:
- `catalog.json` — index of all files
- `crossfirm.json` — cross-company KPI timeseries
- Per-entity period JSONs: `<company>/<entity>/<period>.json`
- `download_all_timeseries.csv` — flat timeseries for all companies

### 5. Deploy

The `website/` directory is a static site. Deploy to Vercel or any static host:

```bash
vercel --prod   # from project root
```

---

## Adding a New Company

1. Create `download_<company>.py` following the existing pattern:
   - Define `FILINGS = [(entity, period, url), ...]`
   - Call `run_pipeline(name, FILINGS, PDF_DIR, TXT_DIR)`

2. Run the full pipeline for that company.

3. Add the company to `build_web_data.py`:
   - Add an entry to `COMPANIES` with `name`, `dir`, `entities`, and `display_name`.

4. Rebuild web data and redeploy.

---

## File Naming

- PDFs and text: `{ENTITY}_{YEAR}Q{QUARTER}.pdf` / `.txt`
- Annual statements: stored as Q4 (e.g., `LNL_2023Q4.pdf`)
- Schedules: `{ENTITY}_{PERIOD}_sched_{type}.csv`

## Dependencies

```bash
pip install requests pdfplumber
```

Node/npm not required — the dashboard is pure HTML + JS (Plotly via CDN).
