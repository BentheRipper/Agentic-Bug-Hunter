"""Tests for memory/tool_notes.py — tool-facing gaps/limitations log."""

import json
import pytest

from memory.tool_notes import ToolNotesLog
from memory.schemas import SchemaError, CURRENT_SCHEMA_VERSION, make_tool_note_entry


class TestToolNotesWrite:

    def test_log_creates_file(self, tmp_hunt_dir):
        path = tmp_hunt_dir / "tool_notes.jsonl"
        log = ToolNotesLog(path)
        entry = make_tool_note_entry(
            target="target.com",
            phase="scope",
            observation="test observation",
            classification="known_limitation",
            needs_followup=True,
        )
        log.log(entry)
        assert path.exists()

    def test_log_writes_valid_jsonl(self, tmp_hunt_dir):
        path = tmp_hunt_dir / "tool_notes.jsonl"
        log = ToolNotesLog(path)
        entry = make_tool_note_entry(
            target="target.com",
            phase="recon",
            observation="httpx had no wall-clock cap before this fix",
            classification="known_limitation",
            needs_followup=False,
        )
        log.log(entry)
        with open(path) as f:
            parsed = json.loads(f.readline())
        assert parsed["target"] == "target.com"
        assert parsed["phase"] == "recon"

    def test_flag_convenience(self, tmp_hunt_dir):
        path = tmp_hunt_dir / "tool_notes.jsonl"
        log = ToolNotesLog(path)
        log.flag(
            target="target.com",
            phase="hunt",
            observation="ambiguous nuclei severity mapping for a custom template",
            classification="newly_discovered",
            needs_followup=True,
            action_taken="tagged INFORMATIONAL pending manual review",
        )
        entries = log.read_all()
        assert len(entries) == 1
        assert entries[0]["classification"] == "newly_discovered"
        assert entries[0]["action_taken"] == "tagged INFORMATIONAL pending manual review"

    def test_log_rejects_invalid_phase(self, tmp_hunt_dir):
        path = tmp_hunt_dir / "tool_notes.jsonl"
        log = ToolNotesLog(path)
        with pytest.raises(SchemaError, match="'phase' must be one of"):
            log.flag(
                target="target.com",
                phase="not-a-real-phase",
                observation="x",
                classification="known_limitation",
                needs_followup=False,
            )

    def test_log_rejects_invalid_classification(self, tmp_hunt_dir):
        path = tmp_hunt_dir / "tool_notes.jsonl"
        log = ToolNotesLog(path)
        with pytest.raises(SchemaError, match="'classification' must be one of"):
            log.flag(
                target="target.com",
                phase="hunt",
                observation="x",
                classification="maybe",
                needs_followup=False,
            )

    def test_log_rejects_non_bool_needs_followup(self, tmp_hunt_dir):
        path = tmp_hunt_dir / "tool_notes.jsonl"
        log = ToolNotesLog(path)
        with pytest.raises(SchemaError, match="'needs_followup' must be a boolean"):
            log.flag(
                target="target.com",
                phase="hunt",
                observation="x",
                classification="known_limitation",
                needs_followup="yes",
            )


class TestToolNotesRead:

    def test_read_empty(self, tmp_hunt_dir):
        log = ToolNotesLog(tmp_hunt_dir / "tool_notes.jsonl")
        assert log.read_all() == []

    def test_read_skips_corrupted(self, tmp_hunt_dir):
        path = tmp_hunt_dir / "tool_notes.jsonl"
        log = ToolNotesLog(path)
        log.flag(target="a.com", phase="hunt", observation="x",
                  classification="known_limitation", needs_followup=False)
        with open(path, "a") as f:
            f.write("not json\n")
        log.flag(target="b.com", phase="hunt", observation="y",
                  classification="known_limitation", needs_followup=False)
        entries = log.read_all()
        assert len(entries) == 2

    def test_read_needs_followup_filters(self, tmp_hunt_dir):
        path = tmp_hunt_dir / "tool_notes.jsonl"
        log = ToolNotesLog(path)
        log.flag(target="a.com", phase="hunt", observation="needs follow-up",
                  classification="newly_discovered", needs_followup=True)
        log.flag(target="b.com", phase="hunt", observation="already resolved",
                  classification="known_limitation", needs_followup=False)
        open_items = log.read_needs_followup()
        assert len(open_items) == 1
        assert open_items[0]["target"] == "a.com"


class TestToolNoteSchema:

    def test_valid_full_entry(self):
        entry = make_tool_note_entry(
            target="target.com",
            phase="autopilot",
            observation="circuit breaker tripped on a CDN that always 403s bots",
            classification="known_limitation",
            needs_followup=False,
            engagement_id="eng-001",
            action_taken="skipped host, moved to next P1",
            session_id="sess-001",
        )
        assert entry["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_valid_minimal_entry(self):
        entry = make_tool_note_entry(
            target="target.com",
            phase="other",
            observation="x",
            classification="newly_discovered",
            needs_followup=True,
        )
        assert "action_taken" not in entry
        assert "engagement_id" not in entry

    def test_invalid_target(self):
        with pytest.raises(SchemaError, match="'target' must be a non-empty string"):
            make_tool_note_entry(
                target="",
                phase="hunt",
                observation="x",
                classification="known_limitation",
                needs_followup=False,
            )

    def test_invalid_observation(self):
        with pytest.raises(SchemaError, match="'observation' must be a non-empty string"):
            make_tool_note_entry(
                target="target.com",
                phase="hunt",
                observation="   ",
                classification="known_limitation",
                needs_followup=False,
            )
