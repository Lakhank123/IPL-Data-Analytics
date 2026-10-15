import io
import json
import zipfile
from src.ingestion import convert_archive


def test_small_cricsheet_fixture(tmp_path):
    fixture = {'info': {'teams':['A','B'],'season':'2024','dates':['2024-04-01'],'outcome':{'winner':'A'}}, 'innings':[{'team':'A','overs':[{'over':0,'deliveries':[{'batter':'X','bowler':'Y','runs':{'batter':4,'extras':0,'total':4}}]}]}]}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('123.json',json.dumps(fixture))
    assert convert_archive(buffer.getvalue(), tmp_path) == (1,1)
    assert '123' in (tmp_path / 'matches.csv').read_text()
