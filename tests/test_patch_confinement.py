from __future__ import annotations

from rfsn_kernel.patch_safety import patch_paths_are_confined


def test_patch_confined_accepts_normal_paths(tmp_path):
    ws = tmp_path
    patch = """diff --git a/foo.txt b/foo.txt
index 1111111..2222222 100644
--- a/foo.txt
+++ b/foo.txt
@@ -1 +1 @@
-old
+new
"""
    ok, reason, files = patch_paths_are_confined(str(ws), patch)
    assert ok, reason
    assert files


def test_patch_confined_rejects_traversal(tmp_path):
    ws = tmp_path
    patch = """diff --git a/../pwn.txt b/../pwn.txt
index 1111111..2222222 100644
--- a/../pwn.txt
+++ b/../pwn.txt
@@ -1 +1 @@
-old
+new
"""
    ok, reason, _files = patch_paths_are_confined(str(ws), patch)
    assert not ok


def test_patch_confined_rejects_absolute(tmp_path):
    ws = tmp_path
    patch = """--- /etc/passwd
+++ /etc/passwd
@@ -1 +1 @@
-old
+new
"""
    ok, reason, _files = patch_paths_are_confined(str(ws), patch)
    assert not ok
