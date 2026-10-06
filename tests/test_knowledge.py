import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import knowledge


class KnowledgeFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_directory.name)
        self.root = self.base / "knowledge"
        self.root.mkdir()
        self.root_patch = patch.object(knowledge, "KNOWLEDGE_DIR", self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.temp_directory.cleanup()

    def test_rejects_traversal_absolute_and_project_paths(self):
        for unsafe in ("../outside.txt", "aws/../../outside.txt", "/etc/passwd", "C:\\project\\secret", "foo\\..\\secret"):
            with self.subTest(path=unsafe):
                with self.assertRaises(ValueError):
                    knowledge.safe_knowledge_path(unsafe)

        with self.assertRaises(ValueError):
            knowledge.safe_knowledge_path(".", allow_root=False)

    def test_rejects_symlinks_resolving_outside_knowledge(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.root / "escape"
        link.symlink_to(outside, target_is_directory=True)

        with self.assertRaises(ValueError):
            knowledge.safe_knowledge_directory("escape")

    def test_create_list_upload_rename_move_and_delete_within_root(self):
        source_folder = knowledge.create_knowledge_folder("", "AWS")
        destination_folder = knowledge.create_knowledge_folder("", "Research")
        destination = knowledge.upload_destination(source_folder, "notes.md")
        destination.write_text("Useful notes", encoding="utf-8")

        root_entries = knowledge.list_knowledge_files("")
        self.assertEqual({entry["type"] for entry in root_entries}, {"folder"})
        self.assertTrue({"AWS", "Research"}.issubset({entry["name"] for entry in root_entries}))
        self.assertTrue({"aws", "linkedin", "documents", "other"}.issubset(
            {entry["name"] for entry in root_entries}
        ))
        self.assertEqual(knowledge.list_knowledge_files(source_folder)[0]["name"], "notes.md")

        moved_path = knowledge.move_knowledge_item("AWS/notes.md", destination_folder)
        self.assertEqual(moved_path, "Research/notes.md")
        renamed_path = knowledge.rename_knowledge_item(moved_path, "guide.pdf")
        self.assertEqual(renamed_path, "Research/guide.pdf")
        self.assertTrue(knowledge.safe_knowledge_file_path(renamed_path).is_file())

        knowledge.delete_knowledge_item(destination_folder)
        self.assertFalse((self.root / destination_folder).exists())

    def test_cannot_move_folder_into_its_descendant_or_replace_existing_item(self):
        knowledge.create_knowledge_folder("", "Parent")
        knowledge.create_knowledge_folder("Parent", "Child")
        knowledge.create_knowledge_folder("", "Target")
        knowledge.create_knowledge_folder("Target", "Child")
        with self.assertRaises(ValueError):
            knowledge.move_knowledge_item("Parent", "Parent/Child")
        with self.assertRaises(FileExistsError):
            knowledge.move_knowledge_item("Parent/Child", "Target")

    def test_supported_upload_types_are_enforced(self):
        knowledge.create_knowledge_folder("", "Docs")
        for filename in ("file.md", "file.txt", "file.pdf"):
            with self.subTest(filename=filename):
                self.assertEqual(knowledge.upload_destination("Docs", filename).name, filename)
        with self.assertRaises(ValueError):
            knowledge.upload_destination("Docs", "script.py")


if __name__ == "__main__":
    unittest.main()
