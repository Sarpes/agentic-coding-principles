"""Ladder rung 3 (input range) for the stage gate: generated garbage must never make check_project raise.

Seeded documents (PER_TYPE per file type, 15 file types) go through check_project on a real temporary git repository whose project is
otherwise complete (every stage passed, so every check is reached). Each run must return (problems, notes) and
finish in a few seconds; a traceback, a GateError or a hang counts as a crash. The seed is fixed, so a failing
document can be rebuilt: the failure message names the file, the index and the kind of document.

Speed: git reads only committed and indexed state, which this test never changes (it rewrites one working file
between runs), so the git command results are memoised for the duration of the test. The repository and every
first call are real git. Without the memo the 7,500 runs take far longer than a unit test should.
"""
import contextlib
import io
import json
import os
import random
import sys
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "agentic-principles" / "scripts"))

import check_gates  # noqa: E402
from check_gates import Problem, check_project  # noqa: E402
import tests.test_check_gates as gate_tests  # noqa: E402  (module import: its test classes must not run twice)

SEED = 20261109
# 100 per file type keeps this test near 35 seconds (each run reads about 40 files from disk, 15 types in all).
# The full 500 per type, the number the design asks for, took 161 seconds when measured (RESULTS.md):
#   ROBUSTNESS_PER_TYPE=500 python -m unittest tests.test_gate_robustness
PER_TYPE = int(os.environ.get("ROBUSTNESS_PER_TYPE", "100"))
SLOW_SECONDS = 5.0
TODAY = date(2026, 1, 3)

# Tokens that steer the parsers into their branches; random lines made of them find edges that random bytes miss.
VOCABULARY = [
    "Size: small", "Size: full", "Size:", "Method: sub-agent", "Cycle: 1", "Cycle: -1", "Cycle: 99999999999999999999",
    "Skill-version: 0.3.0", "Skill-version: 9.9.9", "Skill-version:", "Skill-version: 0.3",
    "Adopted-at: 3", "Adopted-at: 9", "Traits: none", "Traits: web, llm", "Traits:",
    "| Stage | Status | Evidence | Override |", "|---|---|---|---|", "| --- |", "|", "||||", "| | |", "\\|", "| a \\| b |",
    "| 3 Build | passed | commit:abc1234, file:BUILD-LEDGER.md | - |", "| 0 Intake | overridden | - | O1 |",
    "| 9 Nope | open | - | - |", "| 6 Own | reopened | file:OWNERSHIP.md | - |",
    "file:", "commit:", "file:../outside.md", "file:/abs/path", "file:STAGES.md", "commit:zzzzzzz", "commit:" + "a" * 41,
    "### O1. title", "### O2. title", "### O", "#### O1", "- **Status:** open", "- **Status:** closed", "- **Date:** 2026-13-45",
    "- **Re-confirmed for release:** 2026-01-01", "- **Stage:** 3 Build", "- **Why:** none", "- **Why:**",
    "Override: O1", "Override: O99", "Override:", "## File map", "## Dependencies", "## Tests", "## Components",
    "## Reviews", "## Retro", "## Explain-back", "## Full round", "Manifests: manual: reason", "Manifests: manual:",
    "(bulk: reason)", "(bulk:)", "n/a: reason", "n/a", "n/a:", "REQ-1", "REQ-", "ATK-1", "ATK-99999", "(EXAMPLE)",
    "Hand-changed commit: abc1234", "Hand-changed commit:", "Closed: 2026-01-01", "Re-check due: 2026-01-08",
    "Re-check done: -", "Graded by:", "proven", "not applicable", "overridden", "closed", "open",
    "<!--", "-->", "<!-- x -->", "```", "````", "``` py", "~~~", "   ```", "tests/test_a.py", "src/", "/", ".", "..",
    "C-SEC-1", "C-WEB-1", "[", "]", "{", "}", "{\"a\": 1}", "[1, 2]", "null", "\"", "'", "\\", "\x00", "﻿", "\r",
    "flask==3.0.0", "requests>=2", "-r other.txt", "git+https://example.com/x.git", "[project]", "dependencies = [",
    "[tool.poetry]", "[dependency-groups]", "\"dependencies\": {", "\"devDependencies\": 5", "### D1. x", "### 1. x",
    "## Intake", "## Design", "Grilled with:", "Grilled with: x", "| Challenge | Owner's answer | Outcome |",
]
UNICODE = ["ı", "ş", "ğ", "İ", "é", "中文", "\U0001f600", "‮", "​", "́",
           "퟿", "\U0010ffff", " ", " ", " ", "\u0000"]

PASSED_STAGE_7 = "| 7 Retro | passed | file:AI-Agents.md | - |"
AI_LOG = "# AI log\n\n### 1. Title\n\n## Retro\n\nThree mistakes became two rules and one template change.\n"
OVERRIDES_SEED = ("# Overrides\n\n### O1. Skip a review\n\n- **Date:** 2026-01-01\n- **Stage:** 3 Build\n"
                  "- **What was skipped:** the second review\n- **Why:** time\n- **Risk accepted:** a bug\n"
                  "- **How to close:** review it\n- **Status:** open\n- **Closing evidence:** -\n"
                  "- **Re-confirmed for release:** 2026-01-02\n")


class GateRobustness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = gate_tests.GoLiveTiming("run_all")
        cls.addClassCleanup(cls.helper.doCleanups)
        extra = {"requirements.txt": "flask==3.0.0\n",
                 "pyproject.toml": "[project]\nname = \"p\"\ndependencies = [\"requests==2.0.0\"]\n",
                 "package.json": "{\"dependencies\": {\"left-pad\": \"1.3.0\"}}\n",
                 "AI-Agents.md": AI_LOG}
        golive = gate_tests.golive_ok(["C-SEC-1", "C-WEB-1", *[f"ATK-{i}" for i in range(1, 6)]])
        cls.root = cls.helper.project(size="full", comps=("Parser",), golive=golive, extra=extra,
                                      deps=["flask 3.0.0", "requests 2.0.0", "left-pad 1.3.0"], overrides=OVERRIDES_SEED)
        stages = (cls.root / "STAGES.md").read_text(encoding="utf-8")
        stages = stages.replace("| 7 Retro | open | - | - |", PASSED_STAGE_7)
        gate_tests.commit(cls.root, {"STAGES.md": stages}, "retro")
        cls.seeds = {}
        for name in ("STAGES.md", "OVERRIDES.md", "ARCHITECTURE.md", "ATTACKS.md", "REQUIREMENTS.md", "DECISIONS.md",
                     "BUILD-LEDGER.md", "GO-LIVE.md", "OWNERSHIP.md", "AI-Agents.md", "RESULTS.md", "GRILLING.md",
                     "checks/checklist.json", "requirements.txt", "pyproject.toml", "package.json"):
            path = cls.root / name
            if path.is_file():
                cls.seeds[name] = path.read_bytes()
        cls.seeds["OVERRIDES.md"] = OVERRIDES_SEED.encode("utf-8")

    def setUp(self):
        self.addCleanup(self.restore)
        memo = {}
        real = check_gates.git

        def cached(root, *args):
            key = (str(root), args)
            if key not in memo:
                memo[key] = real(root, *args)
            return memo[key]

        patcher = mock.patch.object(check_gates, "git", cached)
        patcher.start()
        self.addCleanup(patcher.stop)

    def restore(self):
        for name, data in self.seeds.items():
            (self.root / name).write_bytes(data)

    # ---- the generator
    def make_document(self, rng: random.Random, seed: bytes, kind: int) -> bytes:
        text = seed.decode("utf-8", "replace")
        lines = text.split("\n")
        if kind == 0:                                           # random bytes
            return bytes(rng.randrange(256) for _ in range(rng.randrange(0, 1500)))
        if kind == 1:                                           # cut anywhere, also inside a multi-byte character
            return seed[:rng.randrange(0, len(seed) + 1)]
        if kind == 2:                                           # truncated tables: lose cells and pipes
            out = []
            for line in lines:
                if line.lstrip().startswith("|") and rng.random() < 0.5:
                    cells = line.split("|")
                    del cells[rng.randrange(len(cells)):rng.randrange(len(cells) + 1)]
                    line = "|".join(cells)
                out.append(line)
            return "\n".join(out).encode("utf-8")
        if kind == 3:                                           # very long lines
            out = list(lines)
            for _ in range(rng.randrange(1, 4)):
                i = rng.randrange(len(out))
                filler = rng.choice(["a", "|", " ", "-", "| ", "`", "<!--", "\\|", "REQ-1 ", "x:"])
                out[i] = out[i] + filler * rng.randrange(1000, 60000)
            return "\n".join(out).encode("utf-8")
        if kind == 4:                                           # lines of only pipes
            return "\n".join(rng.choice(["|", "||", "|||||", "| |", "|-|", "|:-:|", ""]) for _ in range(rng.randrange(1, 60))).encode()
        if kind == 5:                                           # non-ASCII anywhere
            out = list(text)
            for _ in range(rng.randrange(1, 30)):
                out.insert(rng.randrange(len(out) + 1), rng.choice(UNICODE))
            return "".join(out).encode("utf-8", "surrogatepass" if rng.random() < 0.3 else "replace")
        if kind == 6:                                           # CRLF, bare CR and a byte-order mark
            mark = b"\xef\xbb\xbf" if rng.random() < 0.5 else b""
            eol = rng.choice(["\r\n", "\r", "\n\r", "\r\r\n"])
            return mark + eol.join(lines).encode("utf-8")
        if kind == 7:                                           # shuffled, dropped and doubled lines
            out = [line for line in lines if rng.random() < 0.8]
            out += [rng.choice(lines) for _ in range(rng.randrange(0, 6))]
            rng.shuffle(out)
            return "\n".join(out).encode("utf-8")
        picks = [rng.choice(VOCABULARY) for _ in range(rng.randrange(1, 40))]   # kind 8: rule vocabulary
        if rng.random() < 0.5:
            picks += lines[:rng.randrange(len(lines) + 1)]
            rng.shuffle(picks)
        return rng.choice(["\n", "\r\n"]).join(picks).encode("utf-8")

    def hunt(self, per_type):
        """(crashes, slow, runs): every seed file rewritten `per_type` times, each run checked."""
        crashes, slow, runs = [], [], 0
        for name, seed in self.seeds.items():
            rng = random.Random(f"{SEED}:{name}")
            path = self.root / name
            for index in range(per_type):
                kind = index % 9
                data = self.make_document(rng, seed, kind)
                path.write_bytes(data)
                started = time.perf_counter()
                try:
                    problems, notes = check_project(self.root, TODAY)
                    self.assertIsInstance(problems, list)
                    self.assertIsInstance(notes, list)
                    self.assertTrue(all(isinstance(p, Problem) for p in problems))
                    self.assertTrue(all(isinstance(n, str) for n in notes))
                except Exception as error:                      # any raise is the failure this test hunts
                    crashes.append(f"{name} #{index} kind {kind}: {type(error).__name__}: {str(error)[:120]}; "
                                   f"document {data[:80]!r}")
                took = time.perf_counter() - started
                if took > SLOW_SECONDS:
                    slow.append(f"{name} #{index} kind {kind}: {took:.1f}s for {len(data)} bytes")
                runs += 1
            path.write_bytes(seed)
        return crashes, slow, runs

    def test_garbage_never_crashes(self):
        crashes, slow, runs = self.hunt(PER_TYPE)
        self.assertEqual(runs, PER_TYPE * len(self.seeds))
        self.assertEqual(crashes[:10], [], f"{len(crashes)} of {runs} documents crashed the gate (seed {SEED})")
        self.assertEqual(slow[:10], [], f"{len(slow)} documents took over {SLOW_SECONDS}s")

    def test_many_unclosed_comment_openers_finish_quickly(self):
        """Found by the garbage run: a long line of '<!--' with no '-->' made clean_lines quadratic (48 s for 160 KB)."""
        text = "<!--" * 20000
        started = time.perf_counter()
        check_gates.clean_lines(text)
        self.assertLess(time.perf_counter() - started, 1.0)

    def test_the_untouched_project_is_clean(self):
        """The control: the base project has no problems, so a problem later comes from the generated file."""
        problems, notes = check_project(self.root, TODAY)
        self.assertEqual(problems, [])
        self.assertEqual(notes, ["open override O1 (stage 3 Build): see OVERRIDES.md"])

    def test_the_generator_changes_files_and_covers_every_kind(self):
        """A generator that returned the seed unchanged would pass the crash test for nothing."""
        rng = random.Random(SEED)
        seed = self.seeds["ARCHITECTURE.md"]
        changed = {kind: self.make_document(rng, seed, kind) != seed for kind in range(9)}
        self.assertEqual(changed, {kind: True for kind in range(9)})

    def test_the_crash_test_can_fail(self):
        """Prove the loop reports a crash: a gate that raises on a STAGES.md without 'Size' must be caught."""
        real = check_gates.parse_stages

        def broken(text):
            if "Size" not in text:                      # true for every random-bytes document
                raise IndexError("boom")
            return real(text)

        with mock.patch.object(check_gates, "parse_stages", broken):
            crashes, _, runs = self.hunt(30)
        self.assertEqual(runs, 30 * len(self.seeds))
        self.assertTrue(any(c.startswith("STAGES.md") and "IndexError" in c for c in crashes), crashes[:3])


class CompanionsRobustness(unittest.TestCase):
    """check_companions.py promises exit 0 and a printed report whatever the user's settings file holds."""
    KEYS = ["a\x00b@m", "../x@y", "*@*", "a@b@c", "p:q@m", "p?@m", "@m", "p@", "con@nul", "a" * 300 + "@m",
            "x/y@m", "C:\\evil@m", "p@" + "m" * 300, "\u0131@\u015f", "p@m\n", "p@m", "p@m" + "\\" * 3]

    @classmethod
    def setUpClass(cls):
        import check_companions
        cls.module = check_companions
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.claude = Path(cls.tmp.name)
        skill = cls.claude / "plugins" / "cache" / "m" / "p" / "1.0" / "skills"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_bytes(b"---\nname: \xff\xfe\n---\n")

    def run_main(self, settings: bytes):
        (self.claude / "settings.json").write_bytes(settings)
        with contextlib.redirect_stdout(io.StringIO()):
            return self.module.main([str(self.claude)])

    def test_a_plugin_key_with_a_null_character_does_not_crash(self):
        """Found by the garbage run: the NUL made Path.glob raise ValueError and the command exited with a traceback."""
        self.assertEqual(self.run_main(json.dumps({"enabledPlugins": {"a\x00b@m": True}}).encode()), 0)

    def test_garbage_settings_never_crash(self):
        rng = random.Random(f"{SEED}:settings")
        valid = json.dumps({"enabledPlugins": {"p@m": True, "q@m": False}}).encode()
        crashes = []
        for index in range(max(100, PER_TYPE)):
            kind = index % 5
            if kind == 0:
                data = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 300)))
            elif kind == 1:
                data = valid[:rng.randrange(len(valid) + 1)]
            elif kind == 2:
                data = json.dumps({"enabledPlugins": {rng.choice(self.KEYS): rng.choice([True, False, None, 1, [], {}])
                                                      for _ in range(rng.randrange(1, 5))}}).encode()
            elif kind == 3:
                data = rng.choice([b"[", b"{"]) * rng.randrange(1, 200000)         # nesting far beyond the parser's limit
            else:
                data = rng.choice([b"[]", b"null", b"\"x\"", b"1", b"{\"enabledPlugins\": []}", b"\xef\xbb\xbf{}"])
            try:
                self.assertEqual(self.run_main(data), 0)
            except Exception as error:
                crashes.append(f"#{index} kind {kind}: {type(error).__name__}: {str(error)[:100]}; {data[:40]!r}")
        self.assertEqual(crashes[:10], [], f"{len(crashes)} settings files crashed check_companions (seed {SEED})")


if __name__ == "__main__":
    unittest.main()
