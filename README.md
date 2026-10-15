# IPL InsightX ☕ — Coffee Edition

An interactive historical IPL analytics website built for a **Big Data Computing (BDC)** mini-project. The interface uses a warm coffee / cream design, interactive season filters, team analysis, batting and bowling leaderboards, venue exploration, head-to-head comparisons, CSV exports and a Big Data Lab.

## What is inside

- `dashboard/app.py`: full Streamlit website (eight interactive sections).
- `src/ingestion.py`: downloads IPL JSON from Cricsheet and normalizes it to CSV.
- `src/pipeline.py`: executes local PySpark ETL to Silver and Gold Parquet.
- `tests/`: ingestion tests.
- `.streamlit/config.toml`: cream, brown, and coffee theme.
- `data/raw/`, `data/silver/`, `data/gold/`: generated at runtime; the ZIP ships without your existing dataset.

## Install and launch on Windows

Open PowerShell in the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install 'pandas>=2.2,<3'
python -m src.ingestion
python -m streamlit run dashboard/app.py
```

Open the local URL (normally http://localhost:8501). The interactive website requires `data/raw/matches.csv` and `data/raw/deliveries.csv`; it does **not** need to start Spark on each page visit.

To generate the **Big Data Computing** Silver/Gold layers separately:

```powershell
python -m src.pipeline
```

**Windows Spark requirement:** Some Spark/Hadoop distributions require the native Windows Hadoop utilities `winutils.exe` and `hadoop.dll`, matching the Hadoop dependency bundled with your Spark build. Do not create blank placeholder files. Configure `HADOOP_HOME` and `PATH` to point to your verified binaries. Alternatively, use WSL2. Never redistribute unverified third-party binaries as part of this project.

## Data and methodology

- **Primary source:** [Cricsheet Downloads](https://cricsheet.org/downloads/) — IPL ball-by-ball JSON archive.
- **Schema:** [Cricsheet JSON format](https://cricsheet.org/format/json/).
- **ESPNcricinfo:** [ESPNcricinfo cricket coverage](https://www.espncricinfo.com/) is linked for reference only. No live ESPN dataset, scraping, API or ESPN affiliation is implemented.
- No live matches or scores are claimed. Data coverage is determined by when you last ran ingestion.

The starter importer uses one record per delivery and retains the first dismissal if multiple wickets occur on a ball. As a result, aggregate official scorecard wicket totals may differ in rare circumstances. Historical team names remain distinct. Win rate includes all fixtures in the denominator. See the in-app **Data & Sources** page.

## Big Data concepts used

| Concept | Implementation |
|---|---|
| ETL | Python ingestion -> raw CSV -> PySpark Silver / Gold tables |
| Distributed API | Spark DataFrame transformations and aggregations |
| Storage | Column-oriented Parquet |
| Partitioning | Silver delivery records partitioned by season |
| Joins | Deliveries joined to match dimension on match_id |
| Query optimization | Materialized Gold tables and Streamlit cached reads |
| Local computing | Spark `local[*]`, **not** a multi-node cluster or HDFS |
| Frontend analytics | Streamlit, Plotly and cached Pandas exploration |

**Performance benchmarking is not yet implemented.** Do not claim benchmark speedups or a Hadoop distributed cluster in your BDC report.

## Main features

1. Overview: season runs, sixes, top batters and winners.
2. Team Lab: wins, toss influence, season breakdown and rivals.
3. Batting Studio: strike rate, runs, boundary stats, comparison charts.
4. Bowling Studio: wickets, bowling economy, player ranking filters.
5. Venue Explorer: first-innings score distribution and match records.
6. Head-to-Head: historical records, win splits and game list.
7. Big Data Lab: pipeline status, artifact availability, BDC mapping.
8. Data & Sources: source provenance, limitations and samples.

## Quality and performance

- `@st.cache_data` loads 2 raw CSV files once until they change or the cache is cleared. Filtering happens in memory.
- The application uses aggregate summaries and Plotly interactive charts, not Spark processes inside UI callbacks.
- `python -m pytest` runs existing ingestion tests.
- If you change data in-place and see stale results, use the Streamlit menu → Clear cache, then rerun.

## Deployment / sharing

Send a ZIP with project code plus your local `data/raw/` files if the recipient needs an offline runnable dashboard. Do not share `.venv`, `.git`, caches, or `hadoop` executables. Gold tables are optional for the user-facing interface but needed to show completed Spark output on the Big Data Lab page.

For Streamlit Community Cloud, push this repository with an appropriate reproducible data ingestion strategy or hosted CSV/Parquet storage; Cloud will not automatically inherit local data folders. Respect Cricsheet and third-party redistribution terms.

Educational academic mini-project; not associated with IPL, BCCI or ESPNcricinfo.

## Standalone coffee-themed browser website (no Streamlit UI)

This package **also includes an independent HTML/CSS/JavaScript website** in `website/`. Once you have `data/raw/` CSV files (copy them from the original project, or download with ingestion), run:

```powershell
python -m src.export_web
python -m http.server 8080 -d website
```

Open **http://localhost:8080** in a browser. The JSON exporter converts your actual local dataset into `website/analytics.json`, which the browser reads using `fetch()`. Charts use Plotly.js via CDN, so charts require an internet connection unless you bundle Plotly locally. If running from `file:///` instead of the local server, browsers may block the JSON request; use `http.server` as shown. The browser UI has its own navigation, interactive season and team filters, batting/bowling and venue explorations, head-to-head results, downloadable CSV tables, a BDC page and source documentation.

The standalone website **does not require Streamlit** after JSON is exported. The Spark pipeline is retained for your BDC mini-project. `analytics.json` is excluded from the ZIP because your actual CSV files are on your Windows laptop, not in this conversation. Run the exporter after copying those files in.
