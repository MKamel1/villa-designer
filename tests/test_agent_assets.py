"""Generated agent/skill adapters must match their canonical sources (.agents/skills, agents/roles.json).
A hand edit to a generated copy, or a canonical change without regeneration, fails here instead of silently
drifting; before this test nothing ran `sync_agent_assets.py --check` automatically."""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AgentAssets(unittest.TestCase):
    def test_adapters_in_sync(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_agent_assets.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_skill_support_files_are_copied(self):
        # a skill's templates/examples must reach the Claude adapter too (its links would dangle otherwise)
        for f in (ROOT / ".agents" / "skills").rglob("*"):
            if f.is_file():
                rel = f.relative_to(ROOT / ".agents" / "skills")
                self.assertTrue((ROOT / ".claude" / "skills" / rel).is_file(), str(rel))

    def test_defect_learning_skill_is_referenced_from_agents_md(self):
        self.assertIn("defect-learning", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
