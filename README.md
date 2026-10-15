# IPL InsightX

IPL InsightX is a historical Indian Premier League analytics project. It provides two ways to explore match and ball-by-ball data:

- A Streamlit dashboard for interactive analysis directly from CSV files.
- A standalone HTML, CSS, and JavaScript website that reads a generated JSON dataset.

Both interfaces use season filters, interactive charts, analytical tables, and CSV downloads. The project also includes a PySpark ETL pipeline that writes Silver and Gold Parquet datasets.

## Project structure

```text
dashboard/app.py       Streamlit dashboard
src/ingestion.py       Cricsheet JSON archive to raw CSV
src/pipeline.py        PySpark ETL to Silver and Gold Parquet
src/export_web.py      Raw CSV to browser-ready JSON
website/               Standalone browser application
tests/                 Ingestion tests
data/raw/              matches.csv and deliveries.csv (generated or supplied)
data/silver/           Cleaned match and delivery Parquet datasets
data/gold/             Season summary and batting Parquet datasets
```

The `data/` directories are local data artifacts and are not included in source control.

## Data flow and architecture

```text
Cricsheet IPL JSON archive
          |
          v
src.ingestion
          |
          v
data/raw/matches.csv + deliveries.csv
          |                         |
          |                         +--> dashboard/app.py
          |                              Streamlit + Pandas + Plotly
          |
          +--> src.pipeline
          |       PySpark (local[*])
          |          +--> data/silver/matches
          |          +--> data/silver/deliveries (partitioned by season)
          |          +--> data/gold/season_summary
          |          +--> data/gold/batting
          |
          +--> src.export_web
                  +--> website/analytics.json
                           |
                           v
                  website/ (static browser application)
```

The dashboard reads and caches the raw CSV files; it does not start Spark during normal page use. The browser site reads `website/analytics.json`, which is generated from the same CSV inputs. The Spark pipeline is a separate ETL path for the project's distributed-data processing demonstration.

## Setup

The commands below use PowerShell on Windows. From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Python 3.10 or newer is recommended. The Spark ETL requires a working Java runtime compatible with the installed PySpark version. Some Windows Spark installations also require matching Hadoop native utilities.

### Obtain the raw data

If `data/raw/matches.csv` and `data/raw/deliveries.csv` are already available, proceed to run an interface. Otherwise, download and convert the Cricsheet IPL JSON archive:

```powershell
python -m src.ingestion
```

To convert a previously downloaded archive without accessing the network:

```powershell
python -m src.ingestion --zip path\to\ipl_json.zip
```

The importer writes:

- `data/raw/matches.csv`: one row per match, including season, teams, venue, toss, and result.
- `data/raw/deliveries.csv`: one row per delivery event, including batting, bowling, runs, extras, and dismissal fields.

### Run the Streamlit dashboard

```powershell
python -m streamlit run dashboard/app.py
```

Open the local URL printed by Streamlit (normally `http://localhost:8501`). Available views are Overview, Team Lab, Batting Studio, Bowling Studio, Venue Explorer, Head-to-Head, Big Data Lab, and Data & Sources.

### Run the standalone browser website

Generate the website data, then serve the `website` directory:

```powershell
python -m src.export_web
python -m http.server 8080 -d website
```

Open `http://localhost:8080`. Serve the directory over HTTP rather than opening `index.html` directly, so the browser can load `analytics.json`. Plotly.js is loaded from a CDN, so charts require an internet connection.

### Run the Spark ETL

```powershell
python -m src.pipeline
```

The pipeline reads the raw CSV files, validates and joins delivery records with match metadata, writes Silver Parquet datasets, and produces Gold season and batting summaries. Spark runs in local mode (`local[*]`); this project does not configure a multi-node cluster or HDFS.

## Analytics and methodology

The dashboards provide:

- Season-level match, run, six, and winner summaries.
- Team wins, win rates, toss outcomes, and opponent comparisons.
- Batting and bowling leaderboards with qualification filters and player comparisons.
- Venue match records and first-innings score distributions.
- Head-to-head results, historical match lists, and downloadable CSVs.
- A Big Data Lab view describing pipeline outputs and data availability.

The primary data source is the [Cricsheet IPL JSON archive](https://cricsheet.org/downloads/), using its [JSON format](https://cricsheet.org/format/json/). The analysis is historical and reflects the archive available when ingestion was run; it does not provide live scores.

Interpret results with these data limitations in mind:

- The importer emits one row per delivery and retains only the first dismissal when an event contains multiple dismissals.
- `target_runs` is currently blank in the imported match table.
- Historical franchise names are kept as supplied rather than consolidated across name changes.
- Team win rates use all recorded fixtures, including no-results, as the denominator.
- Bowling wicket totals count selected bowler-credited dismissal types only.

## Tests

Run the ingestion tests with:

```powershell
python -m pytest
```
