from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Iterable

# Running SequenceMatcher with autojunk disabled gives the most readable result
# for Markdown, but it can be quadratic on very large repeated inputs.  Common
# prefixes/suffixes are stripped first, which makes ordinary article edits tiny.
# The remaining expensive case uses a bounded fallback.
_MAX_EXACT_DIFF_CELLS = 2_000_000


@dataclass(frozen=True)
class DiffRow:
    kind: str
    old_number: int | None
    old_text: str
    new_number: int | None
    new_text: str


def _linear_equal_length_opcodes(
    old_lines: list[str], new_lines: list[str]
) -> list[tuple[str, int, int, int, int]]:
    """Produce exact linear opcodes when both sides have the same line count."""

    result: list[tuple[str, int, int, int, int]] = []
    start = 0
    current_equal = old_lines[0] == new_lines[0] if old_lines else True
    for index in range(1, len(old_lines)):
        equal = old_lines[index] == new_lines[index]
        if equal != current_equal:
            tag = "equal" if current_equal else "replace"
            result.append((tag, start, index, start, index))
            start = index
            current_equal = equal
    if old_lines:
        tag = "equal" if current_equal else "replace"
        result.append((tag, start, len(old_lines), start, len(new_lines)))
    return result


def _opcodes(
    old_lines: list[str], new_lines: list[str]
) -> Iterable[tuple[str, int, int, int, int]]:
    prefix = 0
    maximum_prefix = min(len(old_lines), len(new_lines))
    while prefix < maximum_prefix and old_lines[prefix] == new_lines[prefix]:
        prefix += 1

    suffix = 0
    maximum_suffix = min(len(old_lines) - prefix, len(new_lines) - prefix)
    while (
        suffix < maximum_suffix
        and old_lines[len(old_lines) - suffix - 1]
        == new_lines[len(new_lines) - suffix - 1]
    ):
        suffix += 1

    if prefix:
        yield ("equal", 0, prefix, 0, prefix)

    old_end = len(old_lines) - suffix
    new_end = len(new_lines) - suffix
    old_middle = old_lines[prefix:old_end]
    new_middle = new_lines[prefix:new_end]
    if old_middle or new_middle:
        if not old_middle:
            middle = [("insert", 0, 0, 0, len(new_middle))]
        elif not new_middle:
            middle = [("delete", 0, len(old_middle), 0, 0)]
        elif len(old_middle) == len(new_middle) and (
            len(old_middle) * len(new_middle) > _MAX_EXACT_DIFF_CELLS
        ):
            # A large same-length region is most safely represented by direct
            # line comparison; this remains exact and cannot become quadratic.
            middle = _linear_equal_length_opcodes(old_middle, new_middle)
        else:
            exact = len(old_middle) * len(new_middle) <= _MAX_EXACT_DIFF_CELLS
            matcher = difflib.SequenceMatcher(
                a=old_middle,
                b=new_middle,
                autojunk=not exact,
            )
            middle = matcher.get_opcodes()
        for tag, i1, i2, j1, j2 in middle:
            yield (tag, i1 + prefix, i2 + prefix, j1 + prefix, j2 + prefix)

    if suffix:
        yield (
            "equal",
            len(old_lines) - suffix,
            len(old_lines),
            len(new_lines) - suffix,
            len(new_lines),
        )


def side_by_side(old: str, new: str) -> list[DiffRow]:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    rows: list[DiffRow] = []
    for tag, i1, i2, j1, j2 in _opcodes(old_lines, new_lines):
        if tag == "equal":
            for offset, (left, right) in enumerate(
                zip(old_lines[i1:i2], new_lines[j1:j2], strict=True)
            ):
                rows.append(
                    DiffRow("equal", i1 + offset + 1, left, j1 + offset + 1, right)
                )
        elif tag == "delete":
            for offset, left in enumerate(old_lines[i1:i2]):
                rows.append(DiffRow("delete", i1 + offset + 1, left, None, ""))
        elif tag == "insert":
            for offset, right in enumerate(new_lines[j1:j2]):
                rows.append(DiffRow("insert", None, "", j1 + offset + 1, right))
        else:
            width = max(i2 - i1, j2 - j1)
            for offset in range(width):
                left = old_lines[i1 + offset] if i1 + offset < i2 else ""
                right = new_lines[j1 + offset] if j1 + offset < j2 else ""
                rows.append(
                    DiffRow(
                        "replace",
                        i1 + offset + 1 if i1 + offset < i2 else None,
                        left,
                        j1 + offset + 1 if j1 + offset < j2 else None,
                        right,
                    )
                )
    return rows


def diff_stats(old: str, new: str) -> tuple[int, int]:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    added = removed = 0
    for tag, i1, i2, j1, j2 in _opcodes(old_lines, new_lines):
        if tag in {"replace", "delete"}:
            removed += i2 - i1
        if tag in {"replace", "insert"}:
            added += j2 - j1
    return added, removed
