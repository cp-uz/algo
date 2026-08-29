from __future__ import annotations

from web.diffing import diff_stats, side_by_side


def test_large_repetitive_diff_is_bounded_and_keeps_single_change_readable() -> None:
    old_lines = ["same"] * 3000
    new_lines = list(old_lines)
    new_lines[1500] = "changed"
    old = "\n".join(old_lines)
    new = "\n".join(new_lines)

    assert diff_stats(old, new) == (1, 1)
    rows = side_by_side(old, new)
    changed = [row for row in rows if row.kind != "equal"]
    assert len(rows) == 3000
    assert changed == [
        type(changed[0])("replace", 1501, "same", 1501, "changed")
    ]


def test_diff_stats_handles_insertions_and_deletions() -> None:
    assert diff_stats("a\nb\nc", "a\ninserted\nb\nc") == (1, 0)
    assert diff_stats("a\nb\nc", "a\nc") == (0, 1)
