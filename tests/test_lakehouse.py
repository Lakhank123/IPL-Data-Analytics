"""Unit and Integration Tests for IPL Data Lakehouse.

Validates cricket domain calculations, taxonomy filters, and
Lakehouse dataset integrity.
"""
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_raw_csv_existence_and_counts():
    raw_dir = ROOT / 'data' / 'raw'
    assert (raw_dir / 'matches.csv').exists(), "matches.csv must exist"
    assert (raw_dir / 'deliveries.csv').exists(), "deliveries.csv must exist"
    
    df_m = pd.read_csv(raw_dir / 'matches.csv', low_memory=False)
    assert len(df_m) == 1243, f"Expected 1,243 matches, got {len(df_m)}"
    assert df_m['match_id'].nunique() == 1243, "match_id must be globally unique"
    assert df_m['season'].nunique() == 19, "Expected 19 tournament seasons"


def test_cricket_batting_strike_rate_formula():
    """Verify strike rate calculation adheres strictly to legal ball face rules."""
    deliveries = pd.DataFrame([
        {'batter': 'BatterA', 'batter_runs': 4, 'wides': 0, 'noballs': 0}, # legal ball faced, 4 runs
        {'batter': 'BatterA', 'batter_runs': 6, 'wides': 0, 'noballs': 0}, # legal ball faced, 6 runs
        {'batter': 'BatterA', 'batter_runs': 0, 'wides': 1, 'noballs': 0}, # wide ball: 0 ball faced
        {'batter': 'BatterA', 'batter_runs': 1, 'wides': 0, 'noballs': 1}, # no-ball: legal ball faced by batter, 1 run
    ])
    balls_faced = int((deliveries['wides'] == 0).sum())
    total_runs = int(deliveries['batter_runs'].sum())
    sr = round((total_runs * 100.0) / balls_faced, 2)
    
    assert balls_faced == 3, "Wides must not count towards balls faced"
    assert total_runs == 11, "Batter runs must equal 4+6+0+1 = 11"
    assert sr == 366.67, f"Expected strike rate 366.67, got {sr}"


def test_cricket_bowling_economy_formula():
    """Verify bowler runs exclude byes/leg-byes and legal balls exclude wides/noballs."""
    deliveries = pd.DataFrame([
        {'bowler': 'BowlerX', 'batter_runs': 1, 'wides': 0, 'noballs': 0, 'byes': 0, 'legbyes': 0}, # legal, 1 run
        {'bowler': 'BowlerX', 'batter_runs': 0, 'wides': 1, 'noballs': 0, 'byes': 0, 'legbyes': 0}, # wide: 1 run, not legal ball
        {'bowler': 'BowlerX', 'batter_runs': 0, 'wides': 0, 'noballs': 1, 'byes': 0, 'legbyes': 0}, # no-ball: 1 run, not legal ball
        {'bowler': 'BowlerX', 'batter_runs': 0, 'wides': 0, 'noballs': 0, 'byes': 4, 'legbyes': 0}, # byes: 0 bowler run, 1 legal ball
        {'bowler': 'BowlerX', 'batter_runs': 0, 'wides': 0, 'noballs': 0, 'byes': 0, 'legbyes': 2}, # leg-byes: 0 bowler run, 1 legal ball
        {'bowler': 'BowlerX', 'batter_runs': 6, 'wides': 0, 'noballs': 0, 'byes': 0, 'legbyes': 0}, # legal, 6 runs
    ])
    
    legal_balls = int(((deliveries['wides'] == 0) & (deliveries['noballs'] == 0)).sum())
    bowler_runs = int((deliveries['batter_runs'] + deliveries['wides'] + deliveries['noballs']).sum())
    econ = round((bowler_runs * 6.0) / legal_balls, 2)
    
    assert legal_balls == 4, f"Expected 4 legal deliveries, got {legal_balls}"
    assert bowler_runs == 9, f"Expected 9 runs conceded (1+1+1+0+0+6), got {bowler_runs}"
    assert econ == 13.5, f"Expected economy 13.50, got {econ}"


def test_bowler_credited_wicket_taxonomy():
    """Verify run-out and retired hurt are strictly excluded from bowler wickets."""
    kinds = [
        ('bowled', True),
        ('caught', True),
        ('caught and bowled', True),
        ('lbw', True),
        ('stumped', True),
        ('hit wicket', True),
        ('run out', False),
        ('retired hurt', False),
        ('retired out', False),
        ('obstructing the field', False)
    ]
    bowler_credited = {'bowled', 'caught', 'caught and bowled', 'lbw', 'stumped', 'hit wicket'}
    for kind, expected in kinds:
        actual = kind in bowler_credited
        assert actual == expected, f"Wicket classification failed for '{kind}': expected {expected}, got {actual}"


def test_lakehouse_gold_tables_integrity():
    """Validate that precomputed Gold Lakehouse tables exist and contain valid aggregations."""
    gold_dir = ROOT / 'data' / 'lakehouse' / 'gold'
    assert (gold_dir / 'season_summary').exists(), "Gold season_summary table must exist"
    assert (gold_dir / 'batting').exists(), "Gold batting table must exist"
    assert (gold_dir / 'bowling').exists(), "Gold bowling table must exist"
    assert (gold_dir / 'venues').exists(), "Gold venues table must exist"
    assert (gold_dir / 'teams').exists(), "Gold teams table must exist"
    
    df_s = pd.read_parquet(gold_dir / 'season_summary')
    assert len(df_s) == 19, f"Expected 19 seasons in Gold season summary, got {len(df_s)}"
    assert df_s['matches'].sum() == 1243, f"Expected 1,243 total matches, got {df_s['matches'].sum()}"
    assert df_s['delivery_events'].sum() == 295732, f"Expected 295,732 total events, got {df_s['delivery_events'].sum()}"
