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


def test_patch_confined_rejects_symlink_escape(tmp_path):
    """
    If a path inside workspace is a symlink pointing outside, APPLY_PATCH must be rejected
    by confinement rules (realpath check).
    """
    ws = tmp_path / "ws"
    ws.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    # Create a symlink inside workspace that points outside
    link = ws / "escape.txt"
    link.symlink_to(outside)

    patch = """diff --git a/escape.txt b/escape.txt
index 1111111..2222222 100644
--- a/escape.txt
+++ b/escape.txt
@@ -1 +1 @@
-old
+new
"""
    ok, reason, _files = patch_paths_are_confined(str(ws), patch)
    assert not ok, reason
    assert "escapes workspace" in reason
