"""Build a small browser-ready JSON analytics payload from real IPL raw CSV files.

Run: python -m src.export_web
The browser application is static; it does not scrape or fetch live cricket APIs.
"""
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def main():
    raw=ROOT/'data'/'raw'; dest=ROOT/'website'/'analytics.json'
    if not (raw/'matches.csv').exists() or not (raw/'deliveries.csv').exists():
        raise FileNotFoundError('First run python -m src.ingestion, or copy your existing data/raw CSVs into this folder.')
    m=pd.read_csv(raw/'matches.csv',dtype={'match_id':'string','season':'string'},low_memory=False).fillna('')
    b=pd.read_csv(raw/'deliveries.csv',dtype={'match_id':'string'},low_memory=False)
    b=b.merge(m[['match_id','season','venue']],on='match_id',how='inner',validate='many_to_one')
    for c in ['batter_runs','total_runs','wides','noballs','is_boundary_non_boundary']:
        b[c]=pd.to_numeric(b[c],errors='coerce').fillna(0)
    b['is_four']=((b.batter_runs==4)&(b.is_boundary_non_boundary==0)).astype(int)
    b['is_six']=((b.batter_runs==6)&(b.is_boundary_non_boundary==0)).astype(int)
    b['bowler_wicket']=b.dismissal_kind.fillna('').isin(['bowled','caught','caught and bowled','lbw','stumped','hit wicket']).astype(int)
    b['legal_ball']=((b.wides==0)&(b.noballs==0)).astype(int)
    b['batter_ball']=(b.wides==0).astype(int)
    b['bowler_runs']=b.batter_runs+b.wides+b.noballs
    season=b.groupby('season',as_index=False).agg(runs=('total_runs','sum'),sixes=('is_six','sum'),fours=('is_four','sum'),events=('match_id','size'))
    counts=m.groupby('season',as_index=False).agg(matches=('match_id','nunique'))
    season=season.merge(counts,on='season')
    bats=b.groupby(['season','batter'],as_index=False).agg(runs=('batter_runs','sum'),balls=('batter_ball','sum'),fours=('is_four','sum'),sixes=('is_six','sum')).sort_values('runs',ascending=False)
    bowls=b.groupby(['season','bowler'],as_index=False).agg(wickets=('bowler_wicket','sum'),runs=('bowler_runs','sum'),balls=('legal_ball','sum')).sort_values('wickets',ascending=False)
    venues=b[b.innings==1].groupby(['season','venue','match_id'],as_index=False).total_runs.sum().groupby(['season','venue'],as_index=False).agg(total=('total_runs','sum'),innings=('match_id','nunique'))
    payload={
        'metadata':{'source':'Cricsheet IPL JSON','generated_by':'src/export_web.py','historical':True,'matches':len(m),'deliveries':len(b)},
        'seasons':season.to_dict('records'),
        'batting':bats.to_dict('records'),
        'bowling':bowls.to_dict('records'),
        'venues':venues.to_dict('records'),
        'matches':m[['match_id','season','date','venue','team1','team2','winner','toss_winner','toss_decision']].to_dict('records'),
    }
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(',',':')),encoding='utf-8')
    print(f'Created {dest} from {len(m):,} matches / {len(b):,} delivery events ({dest.stat().st_size/1024/1024:.2f} MB)')

if __name__=='__main__':main()
