"""IPL InsightX Coffee Edition — interactive analytical application.

Primary source: Cricsheet IPL ball-by-ball JSON, converted by src.ingestion.
Local Spark pipeline: src.pipeline. Detailed interactive views read cached raw CSVs.
"""
from __future__ import annotations
import io
import time
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
GOLD = ROOT / 'data' / 'gold'
BROWN = '#8F6142'
DARK = '#35251D'
CREAM = '#FCF8F2'
BEIGE = '#E8D5BE'
GREEN = '#617A61'
BG = '#F4EDE3'
PLOT = dict(paper_bgcolor=CREAM, plot_bgcolor=CREAM, font_color=DARK,
            font_family='Arial', margin=dict(l=20,r=20,t=55,b=25))

st.set_page_config(page_title='IPL InsightX | Coffee Edition', page_icon='🏏', layout='wide', initial_sidebar_state='expanded')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
html,body,[class*="css"],.stApp {font-family:'DM Sans',sans-serif;color:#35251D}
.stApp {background:#F4EDE3}
[data-testid="stSidebar"] {background:#E8D5BE;border-right:1px solid #D7BEA5}
[data-testid="stSidebar"] * {color:#35251D}
[data-testid="stHeader"] {background:transparent}
.block-container {padding-top:1.45rem;max-width:1450px;padding-bottom:3rem}
h1,h2,h3 {color:#35251D !important} h1 {font-family:'Playfair Display',serif !important}
h2,h3 {letter-spacing:-.4px}
div[data-testid="stMetric"] {background:#FCF8F2;border:1px solid #E5D4C0;padding:18px 20px;border-radius:18px;box-shadow:0 3px 10px rgba(70,43,22,.045)}
div[data-testid="stMetricLabel"] {font-weight:700;color:#795D49}
div[data-testid="stMetricValue"] {color:#35251D;font-weight:800}
.stButton>button[kind="primary"] {background:#8F6142;border-color:#8F6142;color:white;border-radius:12px}
.stButton>button {border-radius:12px}
div[data-testid="stPlotlyChart"] {background:#FCF8F2;border:1px solid #E5D4C0;border-radius:18px;padding:8px}
[data-testid="stDataFrame"] {border-radius:14px;overflow:hidden}
.hero {padding:28px 32px;background:linear-gradient(115deg,#35251D,#805439 76%,#A87C54);border-radius:22px;color:white;margin-bottom:24px}
.hero h1 {color:#FFF8ED !important;margin:0 0 8px;font-size:2.45rem}
.hero p {color:#F1D9BD;margin:0;font-size:1rem}
.eyebrow {letter-spacing:2.2px;text-transform:uppercase;font-size:12px;color:#B98E6E;font-weight:800}
.softnote {background:#FCF8F2;padding:15px 20px;border-radius:14px;border-left:4px solid #8F6142;margin:12px 0}
.stTabs [data-baseweb="tab-list"] {gap:5px}
.stTabs [data-baseweb="tab"] {background:#F0E4D5;border-radius:10px 10px 0 0}
.stTabs [aria-selected="true"] {background:#8F6142;color:white}
</style>''', unsafe_allow_html=True)

@st.cache_data(show_spinner='Preparing the IPL data studio…')
def load_data():
    paths = [RAW / 'matches.csv', RAW / 'deliveries.csv']
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(str(p))
    m = pd.read_csv(paths[0], low_memory=False, dtype={'match_id':'string', 'season':'string'})
    b = pd.read_csv(paths[1], low_memory=False, dtype={'match_id':'string'})
    for col in ['batter_runs','extras','total_runs','wides','noballs','byes','legbyes','penalty','is_boundary_non_boundary','over','innings']:
        b[col] = pd.to_numeric(b[col],errors='coerce').fillna(0)
    m['season'] = m['season'].astype(str)
    m['date'] = pd.to_datetime(m['date'],errors='coerce')
    b = b.merge(m[['match_id','season','date','venue']],on='match_id',how='inner',validate='many_to_one')
    b['valid_ball'] = b['wides'].eq(0) & b['noballs'].eq(0)
    b['batter_ball'] = b['wides'].eq(0)
    b['is_four'] = b['batter_runs'].eq(4) & b['is_boundary_non_boundary'].eq(0)
    b['is_six'] = b['batter_runs'].eq(6) & b['is_boundary_non_boundary'].eq(0)
    b['bowler_runs'] = b['batter_runs'] + b['wides'] + b['noballs']
    b['bowler_wicket'] = b['dismissal_kind'].fillna('').isin({'bowled','caught','caught and bowled','lbw','stumped','hit wicket'})
    b['phase'] = np.select([b['over'] < 6,b['over'] < 15],['Powerplay','Middle overs'],default='Death overs')
    return m,b

@st.cache_data(show_spinner=False)
def gold_info():
    output={}
    for name in ['season_summary','batting']:
        path=GOLD/name
        if path.exists():
            try:
                df=pd.read_parquet(path)
                output[name]={'rows':len(df),'columns':list(df.columns)}
            except Exception as ex:
                output[name]={'error':str(ex)}
    return output

def chart(fig):
    fig.update_layout(**PLOT)
    fig.update_xaxes(showgrid=False,zeroline=False)
    fig.update_yaxes(gridcolor='#EDE0D1',zeroline=False)
    st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False})

def metric_block(stats):
    cols=st.columns(len(stats))
    for c,(label,value) in zip(cols,stats):
        c.metric(label,value)

def caption(text):
    st.caption(text)

def df_download(frame,name):
    st.download_button('⬇ Export table as CSV',frame.to_csv(index=False).encode('utf-8'),file_name=name,mime='text/csv',key=f'download_{name}')

try:
    matches,balls=load_data()
except Exception as exc:
    st.markdown('<div class="hero"><div class="eyebrow">IPL ANALYTICS STUDIO</div><h1>IPL InsightX</h1><p>End-to-end cricket intelligence powered by historical deliveries</p></div>', unsafe_allow_html=True)
    st.error(f'Raw dataset unavailable: {exc}')
    st.code('python -m src.ingestion\npython -m src.pipeline\npython -m streamlit run dashboard/app.py',language='powershell')
    st.info('Use the same project folder when running the commands. The website requires data/raw/matches.csv and data/raw/deliveries.csv.')
    st.stop()

with st.sidebar:
    st.markdown('## ☕ IPL InsightX')
    st.caption('COFFEE EDITION · CRICKET DATA STUDIO')
    st.divider()
    page=st.radio('EXPLORE', ['🏠 Overview','🏆 Team Lab','🏏 Batting Studio','🎯 Bowling Studio','🏟️ Venue Explorer','⚔️ Head-to-Head','🔬 Big Data Lab','📚 Data & Sources'], label_visibility='collapsed')
    st.divider()
    all_seasons=sorted(matches['season'].dropna().unique().tolist(),reverse=True)
    season_choice=st.multiselect('IPL seasons',all_seasons,default=all_seasons)
    if not season_choice:
        st.warning('Choose at least one season.')
        st.stop()
    st.caption(f'{len(season_choice)} season(s) selected')
    st.markdown('---')
    st.caption('Source: Cricsheet · Historical match files')
    st.caption('No live-score or ESPN API connection')

m=matches[matches['season'].isin(season_choice)].copy()
b=balls[balls['season'].isin(season_choice)].copy()
if m.empty or b.empty:
    st.warning('No records available for these seasons.'); st.stop()

st.markdown('<div class="hero"><div class="eyebrow">THE CRICKET DATA STUDIO · 2008 ONWARD</div><h1>IPL InsightX <span style="font-size:1rem;color:#F1D9BD">/ Coffee Edition</span></h1><p>Explore seasons, teams, venues and players with interactive historical IPL analytics.</p></div>',unsafe_allow_html=True)

if page=='🏠 Overview':
    st.subheader('Season pulse')
    metric_block([('Matches',f'{len(m):,}'),('Delivery events',f'{len(b):,}'),('Total runs',f'{int(b.total_runs.sum()):,}'),('Sixes',f'{int(b.is_six.sum()):,}')])
    years=m.groupby('season',as_index=False).agg(matches=('match_id','nunique'))
    runs=b.groupby('season',as_index=False).agg(runs=('total_runs','sum'),sixes=('is_six','sum'),fours=('is_four','sum'))
    yearly=years.merge(runs,on='season').sort_values('season')
    left,right=st.columns([1.65,1])
    with left: chart(px.bar(yearly,x='season',y='runs',color_discrete_sequence=[BROWN],title='Total runs by season'))
    with right: chart(px.line(yearly,x='season',y='sixes',markers=True,color_discrete_sequence=[GREEN],title='Six-hitting trend'))
    a1,a2=st.columns(2)
    with a1:
        top=b.groupby('batter',as_index=False)['batter_runs'].sum().nlargest(10,'batter_runs')
        chart(px.bar(top.sort_values('batter_runs'),x='batter_runs',y='batter',orientation='h',color_discrete_sequence=[BROWN],title='Leading batters — selected seasons'))
    with a2:
        winners=m[m.winner.notna() & m.winner.ne('')].winner.value_counts().head(10).rename_axis('team').reset_index(name='wins')
        chart(px.bar(winners.sort_values('wins'),x='wins',y='team',orientation='h',color_discrete_sequence=[GREEN],title='Most match wins'))
    st.dataframe(yearly,hide_index=True,use_container_width=True)
    df_download(yearly,'ipl_season_summary.csv')

elif page=='🏆 Team Lab':
    st.subheader('Team intelligence')
    teams=sorted(set(m.team1.dropna())|set(m.team2.dropna()))
    team=st.selectbox('Select franchise / historical team',teams)
    tm=m[(m.team1==team)|(m.team2==team)].copy()
    wins=int(tm.winner.eq(team).sum())
    played=len(tm)
    metric_block([('Matches',f'{played:,}'),('Wins',str(wins)),('Recorded win rate',f'{wins/played*100:.1f}%' if played else '—'),('Toss wins',str(int(tm.toss_winner.eq(team).sum())))])
    caption('Win rate uses all team fixtures as the denominator, including no-results. It is not a points-table percentage.')
    l,r=st.columns(2)
    with l:
        by_year=tm.assign(won=tm.winner.eq(team).astype(int)).groupby('season',as_index=False).agg(matches=('match_id','size'),wins=('won','sum'))
        by_year['win_pct']=(100*by_year.wins/by_year.matches).round(1)
        chart(px.bar(by_year.sort_values('season'),x='season',y='win_pct',color_discrete_sequence=[BROWN],title=f'{team} — win rate by season'))
    with r:
        toss=tm.assign(toss_won=tm.toss_winner.eq(team),match_won=tm.winner.eq(team)).groupby('toss_won',as_index=False).agg(matches=('match_id','size'),wins=('match_won','sum'))
        toss['win_pct']=(toss.wins/toss.matches*100).round(1)
        toss['toss_won']=toss['toss_won'].map({True:'Won toss',False:'Lost toss'})
        chart(px.bar(toss,x='toss_won',y='win_pct',color_discrete_sequence=[GREEN],title='Toss outcome vs win percentage'))
    rivals=tm.assign(opponent=np.where(tm.team1.eq(team),tm.team2,tm.team1)).groupby('opponent',as_index=False).agg(matches=('match_id','count'),wins=('winner',lambda s:(s==team).sum())).sort_values('matches',ascending=False)
    rivals['win_pct']=(rivals.wins/rivals.matches*100).round(1)
    st.markdown('#### Opponent breakdown')
    st.dataframe(rivals,hide_index=True,use_container_width=True)
    df_download(rivals,'ipl_team_opponents.csv')

elif page=='🏏 Batting Studio':
    st.subheader('Batting analytics')
    player_stats=b.groupby('batter',as_index=False).agg(runs=('batter_runs','sum'),balls=('batter_ball','sum'),fours=('is_four','sum'),sixes=('is_six','sum'),innings=('match_id','nunique'))
    player_stats['strike_rate']=(100*player_stats.runs/player_stats.balls.replace(0,np.nan)).round(2)
    min_balls=st.slider('Minimum balls faced',0,1000,100,step=25)
    filtered=player_stats[player_stats.balls>=min_balls].sort_values('runs',ascending=False)
    st.dataframe(filtered.head(100),use_container_width=True,hide_index=True)
    df_download(filtered,'ipl_batting_leaderboard.csv')
    l,r=st.columns(2)
    with l: chart(px.bar(filtered.head(12).sort_values('runs'),x='runs',y='batter',orientation='h',color_discrete_sequence=[BROWN],title='Highest run scorers'))
    with r: chart(px.scatter(filtered,x='balls',y='strike_rate',size='runs',hover_name='batter',color_discrete_sequence=[GREEN],title='Strike rate vs balls faced'))
    players=sorted(player_stats.batter.dropna().tolist())
    defaults=[p for p in ['Virat Kohli','Rohit Sharma'] if p in players]
    chosen=st.multiselect('Compare batters (up to 4)',players,default=defaults,max_selections=4)
    if chosen:
        compare=b[b.batter.isin(chosen)].groupby(['season','batter'],as_index=False).agg(runs=('batter_runs','sum'))
        chart(px.line(compare.sort_values('season'),x='season',y='runs',color='batter',markers=True,title='Runs across seasons'))
        st.dataframe(player_stats[player_stats.batter.isin(chosen)],hide_index=True,use_container_width=True)
    caption('Batting strike rate = 100 × batter runs / balls faced; wides excluded from balls faced.')

elif page=='🎯 Bowling Studio':
    st.subheader('Bowling analytics')
    bw=b.groupby('bowler',as_index=False).agg(wickets=('bowler_wicket','sum'),runs_conceded=('bowler_runs','sum'),legal_balls=('valid_ball','sum'),deliveries=('match_id','size'))
    bw['economy']=(bw.runs_conceded*6/bw.legal_balls.replace(0,np.nan)).round(2)
    min_legal=st.slider('Minimum legal deliveries',0,1000,120,step=30)
    qualified=bw[bw.legal_balls>=min_legal].sort_values(['wickets','economy'],ascending=[False,True])
    metric_block([('Qualified bowlers',f'{len(qualified):,}'),('Recorded bowler wickets',f'{int(b.bowler_wicket.sum()):,}'),('Legal balls',f'{int(b.valid_ball.sum()):,}')])
    left,right=st.columns(2)
    with left: chart(px.bar(qualified.head(12).sort_values('wickets'),y='bowler',x='wickets',orientation='h',color_discrete_sequence=[BROWN],title='Leading wicket takers'))
    with right: chart(px.scatter(qualified,x='economy',y='wickets',size='legal_balls',hover_name='bowler',color_discrete_sequence=[GREEN],title='Economy vs wickets'))
    st.dataframe(qualified.head(100),use_container_width=True,hide_index=True)
    df_download(qualified,'ipl_bowling_leaderboard.csv')
    caption('Economy uses batter runs + wides + no-balls, divided by legal balls / 6. Run-outs and other non-bowler wickets are excluded. Multi-dismissal delivery events are not fully represented by the starter importer.')

elif page=='🏟️ Venue Explorer':
    st.subheader('Venue intelligence')
    venue_counts=m.venue.fillna('Unknown').value_counts()
    venues=venue_counts[venue_counts>=5].index.tolist()
    venue=st.selectbox('Choose venue (5+ recorded matches)',venues)
    vm=m[m.venue.eq(venue)].copy()
    vb=b[b.venue.eq(venue)]
    first=vb[vb.innings.eq(1)].groupby('match_id',as_index=False).total_runs.sum()
    metric_block([('Matches',str(len(vm))),('Avg first innings',f'{first.total_runs.mean():.1f}' if len(first) else '—'),('Sixes',f'{int(vb.is_six.sum()):,}'),('Fours',f'{int(vb.is_four.sum()):,}')])
    l,r=st.columns(2)
    with l:
        byseason=vm.groupby('season',as_index=False).agg(matches=('match_id','count')).sort_values('season')
        chart(px.bar(byseason,x='season',y='matches',color_discrete_sequence=[BROWN],title='Matches hosted by season'))
    with r:
        if not first.empty:
            chart(px.histogram(first,x='total_runs',nbins=18,color_discrete_sequence=[GREEN],title='Distribution of first-innings totals'))
    st.markdown('#### Match records at this venue')
    view=vm[['date','season','team1','team2','winner','toss_winner','toss_decision']].sort_values('date',ascending=False)
    st.dataframe(view,hide_index=True,use_container_width=True)
    df_download(view,'ipl_venue_matches.csv')
    caption('Venue names reflect Cricsheet labels and may vary for the same ground. Super-over or shortened matches may affect score distributions.')

elif page=='⚔️ Head-to-Head':
    st.subheader('Head-to-head comparator')
    teams=sorted(set(m.team1.dropna())|set(m.team2.dropna()))
    c1,c2=st.columns(2)
    t1=c1.selectbox('Team A',teams,index=0)
    t2=c2.selectbox('Team B',[t for t in teams if t!=t1],index=0)
    h=m[((m.team1==t1)&(m.team2==t2))|((m.team1==t2)&(m.team2==t1))].copy()
    if h.empty: st.info('No matches between these teams in selected seasons.')
    else:
        w1=int(h.winner.eq(t1).sum()); w2=int(h.winner.eq(t2).sum()); other=len(h)-w1-w2
        metric_block([('Total meetings',len(h)),(f'{t1} wins',w1),(f'{t2} wins',w2),('Other / no winner',other)])
        chart(px.pie(pd.DataFrame({'result':[t1,t2,'Other / no winner'],'matches':[w1,w2,other]}),names='result',values='matches',hole=.60,color_discrete_sequence=[BROWN,GREEN,BEIGE],title='Head-to-head outcomes'))
        view=h[['date','season','team1','team2','venue','winner']].sort_values('date',ascending=False)
        st.dataframe(view,hide_index=True,use_container_width=True)
        df_download(view,'ipl_head_to_head.csv')

elif page=='🔬 Big Data Lab':
    st.subheader('Big Data Computing — Pipeline observability')
    st.markdown('<div class="softnote"><b>Pipeline:</b> Cricsheet JSON → Python ingestion → Raw CSV → PySpark ETL → Silver Parquet (partitioned by season) → Gold Parquet → Analytical website. Spark executes locally; Hadoop Windows tools support filesystem writes, not HDFS storage.</div>',unsafe_allow_html=True)
    status=gold_info()
    metric_block([('Raw matches',f'{len(matches):,}'),('Raw delivery events',f'{len(balls):,}'),('Gold datasets available',f'{len(status)}/2')])
    st.markdown('#### Gold table status')
    audit=[]
    for name in ['season_summary','batting']:
        v=status.get(name)
        audit.append({'dataset':name,'exists':bool(v),'rows':v.get('rows') if v else None,'note':v.get('error','Available') if v else 'Run Spark pipeline'})
    st.dataframe(pd.DataFrame(audit),hide_index=True,use_container_width=True)
    st.markdown('#### Distributed analytics concepts')
    st.markdown('''- **Spark DataFrames:** schema inference, filtering, joins and aggregations.
- **ETL:** raw Bronze CSV → cleaned Silver Parquet → summarized Gold datasets.
- **Partitioning:** delivery Parquet split by season.
- **Spark SQL:** DataFrame aggregation engine, SQL-compatible query execution.
- **Columnar storage:** Parquet analytical data format.
- **Local execution:** `local[*]` parallelism, **not** an HDFS or multi-node cluster.
- **Performance:** Streamlit caches the materialized data rather than running Spark on every click.''')
    rawbytes=sum(p.stat().st_size for p in RAW.glob('*.csv'))
    st.metric('Raw CSV storage',f'{rawbytes/1024/1024:.1f} MB')
    st.markdown('#### Example commands')
    st.code('python -m src.ingestion\npython -m src.pipeline\npython -m streamlit run dashboard/app.py',language='powershell')
    st.info('Benchmarking and cluster deployment are not included in this release. The page reports architecture and existing outputs, not fabricated speedups.')

elif page=='📚 Data & Sources':
    st.subheader('Dataset provenance and methodology')
    st.markdown('''**Primary dataset:** [Cricsheet IPL archive](https://cricsheet.org/downloads/). Downloaded by `src.ingestion`, parsed from match-level JSON into `data/raw/matches.csv` and `data/raw/deliveries.csv`.

**Schema documentation:** [Cricsheet JSON format](https://cricsheet.org/format/json/).

**External cricket reference:** [ESPNcricinfo IPL coverage](https://www.espncricinfo.com/series/indian-premier-league-2025-1449924) provides news, scorecards and contextual cricket reporting. **The website does not scrape or integrate ESPNcricinfo data.** Confirm any permissions and licensing before importing third-party match data.

**Coverage:** This site displays the historical records available in your local Cricsheet download, not live IPL scores. Data was imported from the original source as of the time you ran ingestion.

**Caveats:** Historic team name changes are not merged; result types are not fully normalized; only the first dismissal per delivery is retained in the starter ingestion script; and the batting innings counts here represent matches featuring the batter, not granular official scorecard innings. These are areas for the next data-quality iteration.''')
    st.markdown('#### Sample raw records')
    c1,c2=st.tabs(['Match records','Ball-by-ball records'])
    with c1: st.dataframe(m.head(40),hide_index=True,use_container_width=True)
    with c2: st.dataframe(b[['match_id','innings','over','batter','bowler','total_runs','dismissal_kind']].head(40),hide_index=True,use_container_width=True)
    df_download(m.head(1000),'ipl_match_sample.csv')

st.divider()
st.caption('IPL InsightX · Coffee Edition · Historical analytics from Cricsheet · Built with Python, PySpark, Parquet, Streamlit & Plotly · Not affiliated with IPL or ESPNcricinfo')
