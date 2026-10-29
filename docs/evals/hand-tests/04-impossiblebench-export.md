# Hand test 4: ImpossibleBench rows load and export to task folders

Date: 2026-10-29. Dataset `fjzzq2002/impossible_livecodebench` (linked from the ImpossibleBench README, MIT), loaded with `datasets` under Python 3.12 via uv.

## Result
- Splits `original`, `oneoff`, `conflicting`, 103 rows each. Fields: `task_id`, `prompt`, `test`, `original_test`, `impossible_type`, `entry_point`.
- `docs/evals/harness/export_impossiblebench.py` writes one folder per task: `instruction.md`, `solution.py` (stub), `tests/test_visible.py` (the split's test, visible and writable), `hidden/test_original.py` (unmutated, never copied into the agent's folder), `task.json` with both tests' sha256 and `protected_paths`.
- Checked on `lcbhard_0` (conflicting): the visible test adds `assert candidate(19, 50, 2) == 14` next to the original `== 6`, so the visible suite cannot pass honestly; the original test is the trusted copy for restore-and-rerun.
- `impossible_swebench` also loads (same splits) but needs Docker images per repo; deferred.

## Status
Passed for the LiveCodeBench split. Not yet done: the oracle/empty/wrong-patch validation per task (plan section 5) and the Harbor `environment/Dockerfile`; both come with the grader.
