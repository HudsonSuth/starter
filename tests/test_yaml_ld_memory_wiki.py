import json
import tempfile
import unittest
from pathlib import Path

from core_system.memory.store import FileMemoryStore
from core_system.wiki import import_okf, lift_okf_context, list_notes, seed_wiki
from core_system.yaml_ld import expand_frontmatter, resolve_wiki_links, split_note


ROOT = Path(__file__).resolve().parents[1]


class YamlLdTests(unittest.TestCase):
    def test_wiki_link_resolution(self):
        resolved = resolve_wiki_links(
            {"type": "[[Recipe]]", "requiresIngredient": ["[[Chickpeas]]"]},
            base="https://example.org/",
        )
        self.assertEqual(resolved["type"], "https://example.org/Recipe")
        self.assertEqual(resolved["requiresIngredient"][0], "https://example.org/Chickpeas")

    def test_pyld_expand(self):
        context = {
            "@context": {
                "@base": "https://example.org/",
                "type": "@type",
                "label": "http://www.w3.org/2000/01/rdf-schema#label",
            }
        }
        meta = {"type": "https://example.org/Recipe", "label": "Hummus"}
        expanded = expand_frontmatter(
            meta,
            context=context,
            base="https://example.org/",
            subject_iri="https://example.org/hummus",
        )
        self.assertTrue(expanded)
        self.assertEqual(expanded[0]["@id"], "https://example.org/hummus")


class MemoryTests(unittest.TestCase):
    def test_save_search_delete_rules_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FileMemoryStore(Path(tmp))
            rec = store.save(
                "Use rules-only memory; no paid AI calls",
                bot_name="seed",
                tags="decision,core",
            )
            self.assertTrue(rec.authored_by.startswith("grokbot/"))
            hits = store.search("rules-only")
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0].id, rec.id)
            self.assertTrue(store.delete(rec.id))
            self.assertEqual(store.search("*"), [])


class WikiTests(unittest.TestCase):
    def test_seed_vault_ld_and_okf(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            # Point demos via monkeypatch of module defaults by calling import helpers with paths
            from core_system import wiki as wiki_mod

            vault = wiki_mod.import_vault_ld(
                ROOT / "demos" / "vault-ld",
                wiki,
                bot_name="seed",
            )
            okf = wiki_mod.import_okf(
                ROOT / "demos" / "okf-bundle",
                wiki / "okf",
                bot_name="seed",
            )
            self.assertTrue((vault / "context.jsonld").exists())
            self.assertTrue((okf / "context.jsonld").exists())
            ctx = json.loads((okf / "context.jsonld").read_text(encoding="utf-8"))
            self.assertEqual(ctx, lift_okf_context())
            notes = list_notes(wiki)
            self.assertTrue(any(n["format"] == "vault-ld" for n in notes))
            self.assertTrue(any(n["format"] == "okf" for n in notes))
            hummus = wiki / "Recipes" / "hummus.md"
            meta, _ = split_note(hummus.read_text(encoding="utf-8"))
            self.assertEqual(meta["authoredBy"], "grokbot/seed")
            self.assertEqual(meta["trustTier"], "attested")


if __name__ == "__main__":
    unittest.main()
