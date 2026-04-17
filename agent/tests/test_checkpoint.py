import json
import importlib

checkpoint_module = importlib.import_module("agent.tools.checkpoint")


def test_checkpoint_appends_jsonl_record(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpoint_module, "CHECKPOINT_DIR", tmp_path)

    result = checkpoint_module.checkpoint("inspection_complete", "Inspected VCO and Ladder")

    assert result["status"] == "ok"
    records = (tmp_path / "checkpoints.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(records) == 1
    record = json.loads(records[0])
    assert record["stage"] == "inspection_complete"
    assert record["note"] == "Inspected VCO and Ladder"
    assert record["agent_name"] == "patch_builder"
