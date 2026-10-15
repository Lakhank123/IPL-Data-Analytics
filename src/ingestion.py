"""Download Cricsheet IPL JSON and transform nested match data into two flat CSV tables."""
import argparse
import csv
import io
import json
import urllib.request
import zipfile
from pathlib import Path

URL = "https://cricsheet.org/downloads/ipl_json.zip"
MATCH_COLUMNS = ["match_id", "season", "date", "venue", "team1", "team2", "toss_winner", "toss_decision", "winner", "result_type", "target_runs"]
BALL_COLUMNS = ["match_id", "innings", "over", "ball_index", "batting_team", "bowling_team", "batter", "bowler", "non_striker", "batter_runs", "extras", "total_runs", "wides", "noballs", "byes", "legbyes", "penalty", "dismissal_kind", "player_out", "is_boundary_non_boundary"]


def convert_archive(archive_bytes: bytes, output: Path) -> tuple[int, int]:
    output.mkdir(parents=True, exist_ok=True)
    count_matches = count_balls = 0
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive, (output / 'matches.csv').open('w', newline='', encoding='utf-8') as mf, (output / 'deliveries.csv').open('w', newline='', encoding='utf-8') as bf:
        mw, bw = csv.DictWriter(mf, MATCH_COLUMNS), csv.DictWriter(bf, BALL_COLUMNS)
        mw.writeheader(); bw.writeheader()
        for filename in sorted(archive.namelist()):
            if not filename.lower().endswith('.json') or filename.startswith('__MACOSX/'):
                continue
            data = json.loads(archive.read(filename))
            info = data.get('info', {})
            match_id = Path(filename).stem
            teams = info.get('teams', ['', ''])
            outcome = info.get('outcome', {})
            season = info.get('season', '')
            date = (info.get('dates') or [''])[0]
            mw.writerow(dict(match_id=match_id, season=season, date=date, venue=info.get('venue', ''), team1=teams[0] if len(teams)>0 else '', team2=teams[1] if len(teams)>1 else '', toss_winner=info.get('toss', {}).get('winner',''), toss_decision=info.get('toss', {}).get('decision',''), winner=outcome.get('winner',''), result_type=outcome.get('result',''), target_runs=''))
            count_matches += 1
            for innings_num, innings in enumerate(data.get('innings', []), 1):
                batting_team = innings.get('team', '')
                bowling_team = next((x for x in teams if x != batting_team), '')
                for over in innings.get('overs', []):
                    for ball_index, delivery in enumerate(over.get('deliveries', []), 1):
                        extras = delivery.get('extras', {})
                        runs = delivery.get('runs', {})
                        dismissals = delivery.get('wickets') or []
                        # A delivery can have multiple dismissals; write one delivery row and preserve all details via later upgrades.
                        dismissal = dismissals[0] if dismissals else {}
                        bw.writerow(dict(match_id=match_id, innings=innings_num, over=over.get('over', 0), ball_index=ball_index, batting_team=batting_team, bowling_team=bowling_team, batter=delivery.get('batter',''), bowler=delivery.get('bowler',''), non_striker=delivery.get('non_striker',''), batter_runs=runs.get('batter',0), extras=runs.get('extras',0), total_runs=runs.get('total',0), wides=extras.get('wides',0), noballs=extras.get('noballs',0), byes=extras.get('byes',0), legbyes=extras.get('legbyes',0), penalty=extras.get('penalty',0), dismissal_kind=dismissal.get('kind',''), player_out=dismissal.get('player_out',''), is_boundary_non_boundary=int(bool(runs.get('non_boundary', False)))))
                        count_balls += 1
    return count_matches, count_balls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip', dest='zip_path', type=Path, help='Optional local ipl_json.zip for offline import')
    args = parser.parse_args()
    if args.zip_path:
        raw = args.zip_path.read_bytes()
    else:
        print('Downloading official Cricsheet IPL JSON archive...')
        req = urllib.request.Request(URL, headers={'User-Agent': 'IPL-InsightX-Student-Project/1.0'})
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read()
    matches, balls = convert_archive(raw, Path('data/raw'))
    print(f'Converted {matches:,} matches and {balls:,} delivery events into data/raw/')

if __name__ == '__main__':
    main()
