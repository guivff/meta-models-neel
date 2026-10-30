from pathlib import Path
import json
import pytest
from projects.g_agreement.e96 import separate_watch217 as w

def test_watcher_never_enters_analysis_without_terminal_seals(tmp_path):
 with pytest.raises((FileNotFoundError,ValueError)):w.once(tmp_path)
 assert not (tmp_path/'ANALYSIS_WATCH_CLAIM.json').exists()

def test_existing_analysis_never_replayed(tmp_path,monkeypatch):
 (tmp_path/'analysis_once').mkdir();monkeypatch.setattr(w,'ready',lambda *a:({},{}))
 with pytest.raises(ValueError,match='never replay'):w.once(tmp_path)
 assert not (tmp_path/'ANALYSIS_WATCH_CLAIM.json').exists()

def test_exclusive_claim_prevents_second_worker(tmp_path,monkeypatch):
 (tmp_path/'ANALYSIS_WATCH_CLAIM.json').write_text('{}');monkeypatch.setattr(w,'ready',lambda *a:({},{}))
 with pytest.raises(FileExistsError):w.once(tmp_path)

def test_wrong_terminal_identity_rejected_before_join(tmp_path,monkeypatch):
 p=tmp_path/'packet';j=tmp_path/'judgments';p.mkdir();j.mkdir();monkeypatch.setattr(w,'verify',lambda *a:None)
 (p/'PACKET_SEAL.json').write_text(json.dumps({'scope':{'mode':'separate_slot1_17920'}}))
 (p/'JUDGE_PACKET.json').write_text('[{"id":"a"}]');(p/'OLD_RUBRIC_IDS.json').write_text('[]')
 (j/'JUDGMENT_SEAL.json').write_text(json.dumps({'packet_seal_sha256':w.digest(p/'PACKET_SEAL.json'),'status':'TERMINAL_BLIND_GRID_NO_LABEL_JOIN'}))
 (j/'current_JUDGMENTS.json').write_text('[{"id":"wrong"}]')
 with pytest.raises(ValueError,match='exact separate terminal grid'):w.ready(p,j)
