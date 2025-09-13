from __future__ import annotations

from src.state import StateManager


def test_state_dedupe(tmp_path) -> None:
    s = StateManager(str(tmp_path), "last_seen.json")
    src = 123
    assert s.should_process(src, 10)
    s.mark_processed(src, 10)
    assert not s.should_process(src, 9)
    assert not s.should_process(src, 10)
    assert s.should_process(src, 11)
    s.flush()
    # Reload ensures persistence
    s2 = StateManager(str(tmp_path), "last_seen.json")
    assert not s2.should_process(src, 10)
    assert s2.should_process(src, 12)
