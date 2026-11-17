import unittest

from core_system.authorship import agent_author, is_agent, is_human, normalize_authored_by
from core_system.trust import filter_notes, look_class, normalize_tier


class AuthorshipTests(unittest.TestCase):
    def test_human_only_whsutherland(self):
        self.assertTrue(is_human("human:whsutherland"))
        self.assertFalse(is_human("human:alice"))
        with self.assertRaises(ValueError):
            normalize_authored_by("human:alice")

    def test_agent_prefix(self):
        self.assertEqual(agent_author("research"), "grokbot/research")
        self.assertTrue(is_agent("grokbot/research"))
        self.assertEqual(normalize_authored_by("research"), "grokbot/research")


class TrustTests(unittest.TestCase):
    def test_look_only(self):
        self.assertEqual(look_class("verified"), "trust-verified")
        notes = [
            {"path": "a.md", "trustTier": "verified"},
            {"path": "b.md", "trustTier": "agent-draft"},
        ]
        shown = filter_notes(notes, allow={"verified"})
        self.assertEqual([n["path"] for n in shown], ["a.md"])
        # Filtering never implies access denial — both remain readable in full list
        self.assertEqual(len(filter_notes(notes)), 2)

    def test_unknown_tier(self):
        with self.assertRaises(ValueError):
            normalize_tier("secret")


if __name__ == "__main__":
    unittest.main()
