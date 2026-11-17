"""Agent callers cannot claim a human: actor.

These tests call SaveMemoryTool, FileMemoryStore.save, and the wiki stamp /
import paths. A broken implementation fails them when it:

- stores the write
- rewrites the claim to grokbot/ and stores that
- blocks only the exact string human:whsutherland
- treats case, whitespace, or unicode spoofs as Billy
- rejects ordinary grokbot/ writes, or prose that merely mentions the identity
- lets a valid bot_name hide a human: agent_id
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core_system import HUMAN_AUTHOR
from core_system.authorship import (
    agent_author,
    is_agent,
    is_human,
    normalize_authored_by,
)
from core_system.memory.mcp_server import save_memory_tool
from core_system.memory.store import FileMemoryStore
from core_system.wiki import _stamp_note, import_okf
from core_system.yaml_ld import join_note, split_note

ROOT = Path(__file__).resolve().parents[1]
REFUSAL = "refusing to write human: actor"


def _fullwidth(text: str) -> str:
    out = []
    for ch in text:
        if ch == ":":
            out.append("\uff1a")
        elif "a" <= ch <= "z":
            out.append(chr(0xFF41 + ord(ch) - ord("a")))
        else:
            out.append(ch)
    return "".join(out)


def _math_bold(text: str) -> str:
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr(0x1D41A + ord(ch) - ord("a")))
        else:
            out.append(ch)
    return "".join(out)


# Raw caller input. Detection may fold these; storage must not.
HUMAN_VARIANTS = (
    ("exact", "human:whsutherland"),
    ("case", "Human:whsutherland"),
    ("upper", "HUMAN:WHSUTHERLAND"),
    ("trim", " human:whsutherland\n"),
    ("inner-space", "human: whsutherland"),
    ("tab", "human:\twhsutherland"),
    ("nbsp", "human:\u00a0whsutherland"),
    ("bom", "\ufeffhuman:whsutherland"),
    ("zwsp", "human:\u200bwhsutherland"),
    ("soft-hyphen", "h\u00aduman:whsutherland"),
    ("word-joiner-fullwidth-colon", "\u2060Human\uff1awhsutherland"),
    ("fullwidth", _fullwidth("human:whsutherland")),
    ("math-bold", _math_bold("human") + ":" + _math_bold("whsutherland")),
    ("cyrillic-a", "hum\u0430n:whsutherland"),
    ("cyrillic-capital-a", "hum\u0410n:whsutherland"),
    ("latin-alpha", "hum\u0251n:whsutherland"),
    ("greek-upsilon", "h\u03c5man:whsutherland"),
    ("cyrillic-shha", "\u04bbuman:whsutherland"),
    ("cyrillic-capital-shha", "\u04bauman:whsutherland"),
    ("ratio-colon", "human\u2236whsutherland"),
    ("other-human", "human:alice"),
    ("bare-scheme", "human:"),
    ("suffix", "human:whsutherland/extra"),
)


def _assert_refused(test: unittest.TestCase, exc: BaseException) -> None:
    message = str(exc)
    test.assertIn(REFUSAL, message)
    test.assertIn("not rewritten", message)


class HumanAttestationTests(unittest.TestCase):
    def test_exact_human_attestation_and_variants_are_not_billy(self):
        self.assertTrue(is_human(HUMAN_AUTHOR))
        self.assertEqual(normalize_authored_by(HUMAN_AUTHOR), HUMAN_AUTHOR)
        self.assertFalse(is_agent(HUMAN_AUTHOR))
        with self.assertRaises(ValueError) as blocked:
            normalize_authored_by(HUMAN_AUTHOR, allow_human=False)
        _assert_refused(self, blocked.exception)

        for label, value in HUMAN_VARIANTS:
            with self.subTest(label=label):
                if value == HUMAN_AUTHOR:
                    continue
                self.assertFalse(is_human(value))
                with self.assertRaises(ValueError) as ctx:
                    normalize_authored_by(value)
                _assert_refused(self, ctx.exception)
                with self.assertRaises(ValueError) as agent_ctx:
                    normalize_authored_by(value, allow_human=False)
                _assert_refused(self, agent_ctx.exception)

    def test_agent_author_refuses_human_claims(self):
        self.assertEqual(agent_author("research"), "grokbot/research")
        self.assertEqual(agent_author("humanitarian"), "grokbot/humanitarian")
        for label, value in HUMAN_VARIANTS:
            with self.subTest(label=label):
                with self.assertRaises(ValueError) as ctx:
                    agent_author(value)
                _assert_refused(self, ctx.exception)


class MemoryProvenanceTests(unittest.TestCase):
    def test_store_refuses_human_variants_without_persisting_or_rewriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FileMemoryStore(Path(tmp))
            keeper = store.save("keeper", bot_name="seed")
            self.assertEqual(keeper.authored_by, "grokbot/seed")
            for field in ("agent_id", "bot_name", "authored_by"):
                for label, value in HUMAN_VARIANTS:
                    with self.subTest(field=field, label=label):
                        before = store.index_path.read_text(encoding="utf-8")
                        with self.assertRaises(ValueError) as ctx:
                            store.save(f"smuggle-{field}-{label}", **{field: value})
                        _assert_refused(self, ctx.exception)
                        self.assertEqual(
                            store.index_path.read_text(encoding="utf-8"),
                            before,
                        )
                        self.assertEqual(store.search(f"smuggle-{field}-{label}"), [])
            kept = store.search("keeper")
            self.assertEqual([hit.id for hit in kept], [keeper.id])
            self.assertEqual(kept[0].authored_by, "grokbot/seed")
            self.assertFalse(is_human(kept[0].authored_by))

    def test_human_agent_id_refused_when_another_identity_is_grokbot(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FileMemoryStore(Path(tmp))
            store.save("kept", bot_name="seed")
            before = store.index_path.read_text(encoding="utf-8")
            attempts = (
                {"bot_name": "seed", "agent_id": "human:whsutherland"},
                {"bot_name": "seed", "agent_id": "Human:whsutherland"},
                {"bot_name": "seed", "agent_id": _fullwidth("human:whsutherland")},
                {"authored_by": "grokbot/seed", "agent_id": "human:whsutherland"},
                {"authored_by": "grokbot/seed", "bot_name": "human:alice"},
            )
            for kwargs in attempts:
                with self.subTest(**{k: kwargs[k] for k in kwargs}):
                    with self.assertRaises(ValueError) as ctx:
                        store.save("smuggle-combo", **kwargs)
                    _assert_refused(self, ctx.exception)
                    self.assertEqual(store.index_path.read_text(encoding="utf-8"), before)
            hits = store.search("*")
            self.assertEqual([hit.memory for hit in hits], ["kept"])
            self.assertEqual(hits[0].authored_by, "grokbot/seed")

    def test_grokbot_writes_still_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FileMemoryStore(Path(tmp))
            saved = [
                (store.save("by bot", bot_name="research"), "grokbot/research"),
                (store.save("prefixed", agent_id="grokbot/archivist"), "grokbot/archivist"),
                (store.save("plain", agent_id="archivist"), "grokbot/archivist"),
                (store.save("word", bot_name="humanitarian"), "grokbot/humanitarian"),
                (store.save("unicode bot", bot_name="café"), "grokbot/café"),
                (store.save("default bot"), "grokbot/memory"),
                (store.save("explicit", authored_by="grokbot/explicit"), "grokbot/explicit"),
            ]
            for rec, author in saved:
                with self.subTest(author=author):
                    self.assertEqual(rec.authored_by, author)
                    self.assertTrue(is_agent(rec.authored_by))
                    self.assertFalse(is_human(rec.authored_by))
                    self.assertFalse(rec.authored_by.lower().startswith("human:"))
            self.assertEqual(len(store.search("*")), len(saved))

    def test_prose_and_tags_may_mention_the_human_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FileMemoryStore(Path(tmp))
            text = "Only human:whsutherland counts as human; agents write grokbot/name."
            rec = store.save(text, bot_name="seed", tags="human:whsutherland,decision")
            self.assertEqual(rec.authored_by, "grokbot/seed")
            self.assertEqual(rec.memory, text)
            self.assertIn("human:whsutherland", rec.tags)
            self.assertFalse(is_human(rec.authored_by))

    def test_user_id_does_not_become_authorship(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FileMemoryStore(Path(tmp))
            rec = store.save(
                "Filed for Billy by an agent",
                bot_name="seed",
                user_id="human:whsutherland",
                session_id="session-1",
            )
            self.assertEqual(rec.authored_by, "grokbot/seed")
            self.assertEqual(rec.user_id, "human:whsutherland")
            self.assertFalse(is_human(rec.authored_by))
            self.assertTrue(is_agent(rec.authored_by))

    def test_save_memory_tool_refuses_variants_and_keeps_grokbot_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = FileMemoryStore(Path(tmp))
            with patch("core_system.memory.mcp_server.store", mem):
                for param in ("agent_id", "bot_name"):
                    for label, value in HUMAN_VARIANTS:
                        with self.subTest(param=param, label=label):
                            with self.assertRaises(ValueError) as ctx:
                                save_memory_tool("tool-smuggle", **{param: value})
                            _assert_refused(self, ctx.exception)
                self.assertEqual(mem.search("*"), [])

                with self.assertRaises(ValueError) as hidden:
                    save_memory_tool(
                        "hidden",
                        bot_name="seed",
                        agent_id="human:whsutherland",
                    )
                _assert_refused(self, hidden.exception)
                self.assertEqual(mem.search("*"), [])

                saved = json.loads(save_memory_tool("tool ok", bot_name="research"))
                self.assertEqual(saved["authored_by"], "grokbot/research")
                self.assertFalse(is_human(saved["authored_by"]))
                prefixed = json.loads(
                    save_memory_tool("tool prefixed", agent_id="grokbot/archivist")
                )
                self.assertEqual(prefixed["authored_by"], "grokbot/archivist")
                plain = json.loads(save_memory_tool("tool plain", agent_id="archivist"))
                self.assertEqual(plain["authored_by"], "grokbot/archivist")
                mentioned = json.loads(
                    save_memory_tool(
                        "tool text human:whsutherland",
                        bot_name="seed",
                        user_id="human:whsutherland",
                    )
                )
                self.assertEqual(mentioned["authored_by"], "grokbot/seed")
                self.assertEqual(mentioned["user_id"], "human:whsutherland")
                self.assertEqual(len(mem.search("*")), 4)


class WikiProvenanceTests(unittest.TestCase):
    def test_stamp_refuses_human_provenance_fields_without_rewriting(self):
        cases = {
            "author": "human:whsutherland",
            "Author": "Human:whsutherland",
            "authors": ["grokbot/seed", "human:whsutherland"],
            "authoredBy": " human:whsutherland ",
            "generated.by": _fullwidth("human:alice"),
            "generatedBy": "HUMAN:WHSUTHERLAND",
            "verified-by": "human:whsutherland",
            "verified_by": "h\u00aduman:whsutherland",
            "verifiedBy": {"id": "human:\u200bwhsutherland"},
            "agent_id": "human:whsutherland",
            "bot_name": "\ufeffhuman:whsutherland",
            "ａｕｔｈｏｒ": "human:whsutherland",
            "wrapper": {"generated.by": "Human\uff1awhsutherland"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            for key, value in cases.items():
                with self.subTest(key=key):
                    note = Path(tmp) / f"{key.encode('utf-8').hex()}.md"
                    if key == "wrapper":
                        payload = {"meta": value, "type": "Note"}
                    else:
                        payload = {key: value, "type": "Note"}
                    original = join_note(payload, "Body\n")
                    note.write_text(original, encoding="utf-8")
                    with self.assertRaises(ValueError) as ctx:
                        _stamp_note(
                            note,
                            authored_by="grokbot/seed",
                            trust_tier="agent-draft",
                            format_tag="vault-ld",
                        )
                    _assert_refused(self, ctx.exception)
                    self.assertEqual(note.read_text(encoding="utf-8"), original)

    def test_stamp_allows_non_actor_text_and_grokbot_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            note = Path(tmp) / "note.md"
            note.write_text(
                join_note(
                    {
                        "label": "human:whsutherland",
                        "generated.by": "grokbot/seed",
                        "author": "grokbot/seed",
                        "type": "Note",
                    },
                    "Only human:whsutherland counts as human.\n",
                ),
                encoding="utf-8",
            )
            _stamp_note(
                note,
                authored_by="grokbot/seed",
                trust_tier="agent-draft",
                format_tag="vault-ld",
            )
            meta, body = split_note(note.read_text(encoding="utf-8"))
            self.assertEqual(meta["authoredBy"], "grokbot/seed")
            self.assertEqual(meta["label"], "human:whsutherland")
            self.assertEqual(meta["generated.by"], "grokbot/seed")
            self.assertEqual(meta["trustTier"], "agent-draft")
            self.assertIn("human:whsutherland", body)
            self.assertFalse(is_human(meta["authoredBy"]))

    def test_import_refuses_human_bot_name_without_touching_dest(self):
        bot_names = (
            "human:whsutherland",
            "Human:whsutherland",
            " human:whsutherland ",
            _fullwidth("human:whsutherland"),
            "hum\u0430n:whsutherland",
        )
        for bot_name in bot_names:
            with self.subTest(bot_name=bot_name):
                with tempfile.TemporaryDirectory() as tmp:
                    dest = Path(tmp) / "wiki"
                    dest.mkdir()
                    marker = dest / "keep.txt"
                    marker.write_text("keep", encoding="utf-8")
                    with self.assertRaises(ValueError) as ctx:
                        import_okf(
                            ROOT / "demos" / "okf-bundle",
                            dest,
                            bot_name=bot_name,
                        )
                    _assert_refused(self, ctx.exception)
                    self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
                    self.assertFalse((dest / "index.md").exists())

    def test_import_refuses_human_provenance_in_source(self):
        injections = (
            ("verified-by", "human:whsutherland"),
            ("generated.by", "Human:whsutherland"),
            ("author", _fullwidth("human:whsutherland")),
        )
        for key, value in injections:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as tmp:
                    src = Path(tmp) / "src"
                    shutil.copytree(ROOT / "demos" / "okf-bundle", src)
                    index = src / "index.md"
                    meta, body = split_note(index.read_text(encoding="utf-8"))
                    meta[key] = value
                    index.write_text(join_note(meta, body), encoding="utf-8")
                    dest = Path(tmp) / "dest"
                    dest.mkdir()
                    (dest / "keep.txt").write_text("keep", encoding="utf-8")
                    with self.assertRaises(ValueError) as ctx:
                        import_okf(src, dest, bot_name="seed")
                    _assert_refused(self, ctx.exception)
                    self.assertEqual((dest / "keep.txt").read_text(encoding="utf-8"), "keep")
                    self.assertFalse((dest / "index.md").exists())

    def test_import_allows_prose_mention_of_human_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src"
            shutil.copytree(ROOT / "demos" / "okf-bundle", src)
            index = src / "index.md"
            meta, body = split_note(index.read_text(encoding="utf-8"))
            body += "\nBilly's actor is human:whsutherland.\n"
            index.write_text(join_note(meta, body), encoding="utf-8")
            dest = Path(tmp) / "dest"
            import_okf(src, dest, bot_name="seed")
            stamped, stamped_body = split_note((dest / "index.md").read_text(encoding="utf-8"))
            self.assertEqual(stamped["authoredBy"], "grokbot/seed")
            self.assertEqual(stamped["trustTier"], "provisional")
            self.assertIn("human:whsutherland", stamped_body)
            self.assertFalse(is_human(stamped["authoredBy"]))


if __name__ == "__main__":
    unittest.main()
