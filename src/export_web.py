"""Build a small browser-ready JSON analytics payload from Delta Lake / Spark Gold tables.

Run: python -m src.export_web
Sources precomputed metrics directly from the Data Lakehouse Gold layer.
"""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = ROOT / 'data' / 'raw'
    gold_lakehouse = ROOT / 'data' / 'lakehouse' / 'gold'
    gold_parquet = ROOT / 'data' / 'gold'
    dest = ROOT / 'website' / 'analytics.json'
    
    if not (raw / 'matches.csv').exists():
        raise FileNotFoundError(
            'First run python -m src.ingestion, or verify data/raw/matches.csv exists.'
        )
        
    m = pd.read_csv(
        raw / 'matches.csv',
        dtype={'match_id': 'string', 'season': 'string'},
        low_memory=False
    ).fillna('')

    # Determine data source: Prefer Gold Lakehouse / Parquet if available
    used_lakehouse = False
    if (gold_lakehouse / 'season_summary').exists() and (gold_lakehouse / 'batting').exists():
        print("Exporting web payload directly from Spark Delta Lakehouse Gold tables...")
        season_df = pd.read_parquet(gold_lakehouse / 'season_summary')
        season_df = season_df.rename(columns={'delivery_events': 'events', 'total_runs': 'runs'})
        
        batting_df = pd.read_parquet(gold_lakehouse / 'batting')
        batting_df = batting_df.rename(columns={'balls_faced': 'balls'}).sort_values('runs', ascending=False)
        
        bowling_df = pd.read_parquet(gold_lakehouse / 'bowling')
        bowling_df = bowling_df.rename(columns={'runs_conceded': 'runs', 'legal_deliveries': 'balls'}).sort_values('wickets', ascending=False)
        
        venues_df = pd.read_parquet(gold_lakehouse / 'venues')
        venues_df = venues_df.rename(columns={'total_first_innings_runs': 'total', 'innings_count': 'innings'})
        
        deliveries_count = int(season_df['events'].sum())
        used_lakehouse = True
    elif (gold_parquet / 'season_summary').exists() and (gold_parquet / 'batting').exists():
        print("Exporting web payload from Spark Gold Parquet tables...")
        season_df = pd.read_parquet(gold_parquet / 'season_summary')
        season_df = season_df.rename(columns={'delivery_events': 'events', 'total_runs': 'runs'})
        
        batting_df = pd.read_parquet(gold_parquet / 'batting')
        batting_df = batting_df.rename(columns={'balls_faced': 'balls'}).sort_values('runs', ascending=False)
        
        # Bowling and venues fallback from raw deliveries
        b = pd.read_csv(raw / 'deliveries.csv', dtype={'match_id': 'string'}, low_memory=False)
        b = b.merge(m[['match_id', 'season', 'venue']], on='match_id', how='inner')
        for c in ['batter_runs', 'total_runs', 'wides', 'noballs', 'is_boundary_non_boundary']:
            b[c] = pd.to_numeric(b[c], errors='coerce').fillna(0)
        b['bowler_wicket'] = b.dismissal_kind.fillna('').isin(['bowled', 'caught', 'caught and bowled', 'lbw', 'stumped', 'hit wicket']).astype(int)
        b['legal_ball'] = ((b.wides == 0) & (b.noballs == 0)).astype(int)
        b['bowler_runs'] = b.batter_runs + b.wides + b.noballs
        bowling_df = b.groupby(['season', 'bowler'], as_index=False).agg(
            wickets=('bowler_wicket', 'sum'), runs=('bowler_runs', 'sum'), balls=('legal_ball', 'sum')
        ).sort_values('wickets', ascending=False)
        venues_df = b[b.innings == 1].groupby(['season', 'venue', 'match_id'], as_index=False).total_runs.sum().groupby(
            ['season', 'venue'], as_index=False
        ).agg(total=('total_runs', 'sum'), innings=('match_id', 'nunique'))
        deliveries_count = len(b)
        used_lakehouse = True
    else:
        print("Notice: Gold Lakehouse tables not detected. Computing from raw CSV files...")
        b = pd.read_csv(raw / 'deliveries.csv', dtype={'match_id': 'string'}, low_memory=False)
        b = b.merge(m[['match_id', 'season', 'venue']], on='match_id', how='inner', validate='many_to_one')
        for c in ['batter_runs', 'total_runs', 'wides', 'noballs', 'is_boundary_non_boundary']:
            b[c] = pd.to_numeric(b[c], errors='coerce').fillna(0)
        b['is_four'] = ((b.batter_runs == 4) & (b.is_boundary_non_boundary == 0)).astype(int)
        b['is_six'] = ((b.batter_runs == 6) & (b.is_boundary_non_boundary == 0)).astype(int)
        b['bowler_wicket'] = b.dismissal_kind.fillna('').isin(['bowled', 'caught', 'caught and bowled', 'lbw', 'stumped', 'hit wicket']).astype(int)
        b['legal_ball'] = ((b.wides == 0) & (b.noballs == 0)).astype(int)
        b['batter_ball'] = (b.wides == 0).astype(int)
        b['bowler_runs'] = b.batter_runs + b.wides + b.noballs
        
        season_df = b.groupby('season', as_index=False).agg(
            runs=('total_runs', 'sum'), sixes=('is_six', 'sum'), fours=('is_four', 'sum'), events=('match_id', 'size')
        )
        counts = m.groupby('season', as_index=False).agg(matches=('match_id', 'nunique'))
        season_df = season_df.merge(counts, on='season')
        
        batting_df = b.groupby(['season', 'batter'], as_index=False).agg(
            runs=('batter_runs', 'sum'), balls=('batter_ball', 'sum'), fours=('is_four', 'sum'), sixes=('is_six', 'sum')
        ).sort_values('runs', ascending=False)
        
        bowling_df = b.groupby(['season', 'bowler'], as_index=False).agg(
            wickets=('bowler_wicket', 'sum'), runs=('bowler_runs', 'sum'), balls=('legal_ball', 'sum')
        ).sort_values('wickets', ascending=False)
        
        venues_df = b[b.innings == 1].groupby(['season', 'venue', 'match_id'], as_index=False).total_runs.sum().groupby(
            ['season', 'venue'], as_index=False
        ).agg(total=('total_runs', 'sum'), innings=('match_id', 'nunique'))
        deliveries_count = len(b)

    payload = {
        'metadata': {
            'source': 'Cricsheet IPL JSON Archive',
            'generated_by': 'Apache Spark & Delta Lake Gold Layer (src/lakehouse_pipeline.py)' if used_lakehouse else 'src/export_web.py',
            'lakehouse_engine': 'Delta Lake + Apache Spark 3.5.5' if used_lakehouse else 'None',
            'historical': True,
            'matches': len(m),
            'deliveries': deliveries_count,
        },
        'seasons': season_df[['season', 'runs', 'sixes', 'fours', 'events', 'matches']].to_dict('records'),
        'batting': batting_df[['season', 'batter', 'runs', 'balls', 'fours', 'sixes']].to_dict('records'),
        'bowling': bowling_df[['season', 'bowler', 'wickets', 'runs', 'balls']].to_dict('records'),
        'venues': venues_df[['season', 'venue', 'total', 'innings']].to_dict('records'),
        'matches': m[['match_id', 'season', 'date', 'venue', 'team1', 'team2', 'winner', 'toss_winner', 'toss_decision']].to_dict('records'),
    }
    
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(',', ':')), encoding='utf-8')
    print(f'Successfully created {dest} from Lakehouse Gold outputs ({dest.stat().st_size/1024/1024:.2f} MB)')


if __name__ == '__main__':
    main()
