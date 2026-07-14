"""Regression tests for field-target state in the control server."""

import ast
from pathlib import Path


SERVER_PATH = (
    Path(__file__).resolve().parents[1]
    / "Instruments"
    / "instrument_control_server.py"
)


def _is_desired_field_assignment(node):
    return (
        isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "desired_field_G"
            for target in node.targets
        )
    )


def test_set_field_updates_desired_target_only_after_success():
    """A failed SET_FIELD must preserve the last successful hold target."""
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))

    set_field_case = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.match_case):
            continue
        pattern = node.pattern
        if (
            isinstance(pattern, ast.MatchValue)
            and isinstance(pattern.value, ast.Constant)
            and pattern.value.value == b"SET_FIELD"
        ):
            set_field_case = node
            break

    assert set_field_case is not None, "Could not find the SET_FIELD case"

    try_node = next(
        (node for node in set_field_case.body if isinstance(node, ast.Try)),
        None,
    )
    assert try_node is not None, "SET_FIELD no longer guards ramp_field"

    assignments_before_try = [
        node
        for node in set_field_case.body
        if node is not try_node and _is_desired_field_assignment(node)
    ]
    assert assignments_before_try == []

    successful_assignments = [
        node for node in try_node.orelse if _is_desired_field_assignment(node)
    ]
    assert len(successful_assignments) == 1
