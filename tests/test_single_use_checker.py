from pathlib import Path
import subprocess
import sys


def _run_checker(tmp_path, source: str):
    sample = tmp_path / "sample.py"
    sample.write_text(source, encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[1]
    return subprocess.run(
        [
            sys.executable,
            str(repo_root / ".github/scripts/check_single_use.py"),
            str(sample),
        ],
        capture_output=True,
        cwd=repo_root,
        encoding="utf-8",
        check=False,
    )


def test_unpacking_assignment_is_allowed(tmp_path):
    result = _run_checker(
        tmp_path,
        "left, right = make_pair()\nprint(left)\nprint(right)\n",
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_single_assignment_still_flags(tmp_path):
    result = _run_checker(
        tmp_path,
        "bla = afunction()\nprint(bla)\n",
    )

    assert result.returncode == 1
    assert (
        "`bla` is a module-level variable that is defined once "
        "and used once." in result.stdout
    )


def test_chained_assignment_still_flags(tmp_path):
    result = _run_checker(
        tmp_path,
        "left = right = make_value()\nprint(left)\nprint(right)\n",
    )

    assert result.returncode == 1
    assert (
        "`left` is a module-level variable that is defined once "
        "and used once." in result.stdout
    )
    assert (
        "`right` is a module-level variable that is defined once "
        "and used once."
        in result.stdout
    )


def test_with_alias_assignment_is_allowed(tmp_path):
    result = _run_checker(
        tmp_path,
        (
            "from contextlib import nullcontext\n"
            "with nullcontext('value') as first, nullcontext(first) as second:\n"
            "    print(second)\n"
        ),
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_for_loop_target_is_allowed(tmp_path):
    result = _run_checker(
        tmp_path,
        "for idx in values:\n    print(idx)\n",
    )

    assert result.returncode == 0, result.stdout + result.stderr
