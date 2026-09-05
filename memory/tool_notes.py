"""
Tool notes log — tool-facing knowledge, the counterpart to journal.jsonl's
target-facing knowledge.

journal.jsonl / patterns.jsonl capture what was found on a target and what
technique worked. Neither has a place for the agent itself hitting a
limitation, an ambiguous situation, or a gap worth fixing later — that
only survived if someone happened to mention it afterward. This is that
place: append-only JSONL at hunt-memory/tool_notes.jsonl, written by
/flag, built on the same plumbing as audit.jsonl (memory/audit_log.py's
write pattern) and patterns.jsonl (memory/pattern_db.py's read/validate
skip-on-corruption pattern).
"""

import fcntl
import json
import os
import sys
from pathlib import Path

from memory.rotation import DEFAULT_KEEP, DEFAULT_MAX_BYTES, rotate_if_needed
from memory.schemas import make_tool_note_entry, validate_tool_note_entry, SchemaError


class ToolNotesLog:
    """Append-only log for tool-facing gaps, limitations, and open questions."""

    def __init__(
        self,
        path: str | Path,
        max_bytes: int = DEFAULT_MAX_BYTES,
        keep_backups: int = DEFAULT_KEEP,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.keep_backups = keep_backups

    def log(self, entry: dict) -> None:
        """Validate and append a tool note entry."""
        validated = validate_tool_note_entry(entry)
        line = json.dumps(validated, separators=(",", ":")) + "\n"
        encoded = line.encode("utf-8")

        rotate_if_needed(self.path, max_bytes=self.max_bytes, keep=self.keep_backups)

        fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                written = os.write(fd, encoded)
                if written != len(encoded):
                    raise OSError(f"Partial write: {written}/{len(encoded)} bytes")
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def flag(
        self,
        target: str,
        phase: str,
        observation: str,
        classification: str,
        needs_followup: bool,
        engagement_id: str | None = None,
        action_taken: str | None = None,
        session_id: str | None = None,
    ) -> None:
        """Convenience method: build + log a tool note entry in one call.

        Mirrors AuditLog.log_request() — same "make the entry, then log it"
        shape as every other writer on this plumbing.
        """
        entry = make_tool_note_entry(
            target=target,
            phase=phase,
            observation=observation,
            classification=classification,
            needs_followup=needs_followup,
            engagement_id=engagement_id,
            action_taken=action_taken,
            session_id=session_id,
        )
        self.log(entry)

    def read_all(self) -> list[dict]:
        """Read all tool note entries. Corrupted or invalid lines are skipped with a warning."""
        if not self.path.exists():
            return []

        entries = []
        with open(self.path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    print(
                        f"WARNING: {self.path} line {lineno} is corrupted "
                        f"(skipping): {e}",
                        file=sys.stderr,
                    )
                    continue

                try:
                    validate_tool_note_entry(entry)
                except SchemaError as e:
                    print(
                        f"WARNING: {self.path} line {lineno} failed "
                        f"validation (skipping): {e}",
                        file=sys.stderr,
                    )
                    continue

                entries.append(entry)

        return entries

    def read_needs_followup(self) -> list[dict]:
        """Entries still waiting on follow-up — the queue the next round of
        fixes should read from, oldest first."""
        return [e for e in self.read_all() if e.get("needs_followup") is True]
