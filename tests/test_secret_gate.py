"""The pre-commit secret gate in .githooks/ really refuses a commit, run as a subprocess.

A temporary git repository gets this repository's hooks through core.hooksPath. The hook looks
for the gate script at <top level of the repository being committed>/.githooks/secret_gate.py,
so the temporary repository also holds a copy of that script, as a project that uses the gate does.
The fake key is built at run time from random hex; no key-like literal is stored in this file.
"""
import secrets
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / ".githooks"


def working_python_on_path() -> bool:
    """The hook accepts python3, python or py, but only one that really runs (not a Store stub)."""
    for name in ("python3", "python", "py"):
        if shutil.which(name) is None:
            continue
        try:
            done = subprocess.run([name, "-c", "print('gate-ok')"], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if done.stdout.strip() == "gate-ok":
            return True
    return False


def skip_reason() -> str:
    if shutil.which("git") is None:
        return "git is not on PATH"
    if shutil.which("sh") is None and sys.platform != "win32":
        return "sh is not on PATH"
    if not working_python_on_path():
        return "no working python3, python or py on PATH: the hook would refuse every commit"
    return ""


@unittest.skipIf(skip_reason(), skip_reason() or "unreachable")
class SecretGate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        self.git("init", "-q")
        self.git("config", "core.hooksPath", str(HOOKS))
        (self.repo / ".githooks").mkdir()
        shutil.copy(HOOKS / "secret_gate.py", self.repo / ".githooks" / "secret_gate.py")

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                               "-c", "commit.gpgsign=false", *args],
                              cwd=self.repo, capture_output=True, text=True)

    def commit(self, name, content):
        (self.repo / name).write_text(content, encoding="utf-8")
        self.git("add", name)
        return self.git("commit", "-q", "-m", "test")

    def test_commit_with_a_key_like_line_is_refused(self):
        fake = "EXAMPLE_API_KEY=" + secrets.token_hex(16)
        done = self.commit("settings.txt", fake + "\n")
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("REFUSED", done.stderr)
        self.assertNotIn(fake.split("=", 1)[1], done.stderr)          # the value is never shown
        self.assertEqual(self.git("rev-parse", "--verify", "HEAD").returncode != 0, True)  # no commit made

    def test_commit_of_a_file_named_like_an_env_file_is_refused(self):
        done = self.commit("local.env", "nothing secret in the content\n")
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("REFUSED", done.stderr)
        self.assertNotEqual(self.git("rev-parse", "--verify", "HEAD").returncode, 0)  # no commit made

    def test_harmless_file_commits(self):
        done = self.commit("notes.txt", "nothing secret here\n")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.git("rev-parse", "--verify", "HEAD").returncode, 0)


if __name__ == "__main__":
    unittest.main()
