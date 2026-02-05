from __future__ import annotations

from pathlib import Path

from rfsn_kernel.types import Action, Proposal, StateSnapshot
from rfsn_kernel.gate import gate
from rfsn_kernel.controller import execute_decision


def test_apply_patch_then_run_tests_host(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "x.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (ws / "test_x.py").write_text("from x import f\ndef test_f():\n    assert f() == 2\n", encoding="utf-8")

    # init git so APPLY_PATCH works
    import subprocess
    subprocess.run(["git", "init"], cwd=str(ws), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(ws), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(ws), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "add", "."], cwd=str(ws), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(ws), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    patch = """diff --git a/x.py b/x.py
index 1111111..2222222 100644
--- a/x.py
+++ b/x.py
@@ -1,2 +1,2 @@
 def f():
-    return 1
+    return 2
"""
    st = StateSnapshot(workspace=str(ws), notes={"task_id": "t"})
    prop = Proposal(
        actions=(
            Action("APPLY_PATCH", payload={"patch": patch}),
            Action("RUN_TESTS", payload={"argv": ["pytest", "-q"], "mode": "host"}),
        ),
        meta={},
    )
    d = gate(st, prop)
    assert d.allowed is True
    res = execute_decision(st, d)
    assert res[0].ok is True
    assert res[1].ok is True
