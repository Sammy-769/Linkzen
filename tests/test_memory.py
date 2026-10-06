import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import memory
from retrieval import memory_retrieval_query


class MemoryIntentTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.memory_path_patch = patch.object(
            memory, "MEMORY_FILE", Path(self.temp_directory.name) / "memory.json"
        )
        self.memory_path_patch.start()

    def tearDown(self):
        self.memory_path_patch.stop()
        self.temp_directory.cleanup()

    def test_saves_new_trailing_explicit_memory(self):
        statement = "I have 2.5K LinkedIn followers. Remember this."

        explicit_memory = memory.get_explicit_memory(statement)
        result = memory.add_memory(explicit_memory, return_result=True)

        self.assertEqual(result["action"], "ADD")
        self.assertEqual(result["memory"]["memory"], "I have 2.5K LinkedIn followers")
        self.assertEqual(len(memory.get_memories()), 1)

    def test_name_and_profile_questions_retrieve_saved_profile(self):
        profile_text = (
            "My name is Ada Lovelace. I have an IT support background and am "
            "working towards becoming a Cloud Engineer."
        )
        memory.add_memory(
            profile_text,
            category="goal",
        )

        for question in ("What is my name?", "What do you know about me?"):
            with self.subTest(question=question):
                context, _selected = memory.get_relevant_memory_text(
                    memory_retrieval_query(question),
                    return_details=True,
                )
                self.assertIn("Ada Lovelace", context)
                self.assertEqual(context, f"- {profile_text}")

    def test_name_question_excludes_unrelated_memory_that_mentions_name(self):
        name_text = "My name is Ada Lovelace."
        memory.add_memory(
            name_text,
            category="work",
        )
        memory.add_memory(
            "The name of my current project is Cloud Notes.",
            category="project",
        )

        context, _selected = memory.get_relevant_memory_text(
            memory_retrieval_query("What is my name?"),
            return_details=True,
        )

        self.assertIn("Ada Lovelace", context)
        self.assertNotIn("Cloud Notes", context)
        self.assertEqual(context, f"- {name_text}")

    def test_career_goal_query_selects_goal_not_unrelated_memory(self):
        goal_text = "I am working towards becoming a Cloud Engineer."
        memory.add_memory(
            goal_text,
            category="goal",
        )
        memory.add_memory(
            "I prefer short, direct explanations.",
            category="communication",
        )

        context, _selected = memory.get_relevant_memory_text(
            memory_retrieval_query("What are my career goals?"),
            return_details=True,
        )

        self.assertIn("Cloud Engineer", context)
        self.assertEqual(context, f"- {goal_text}")

    def test_unrelated_question_does_not_receive_saved_memories(self):
        memory.add_memory("My name is Ada Lovelace.", category="work")
        memory.add_memory("I am working towards becoming a Cloud Engineer.", category="goal")

        context, selected = memory.get_relevant_memory_text(
            "What is the capital of France?",
            return_details=True,
        )

        self.assertEqual(context, "")
        self.assertEqual(selected, [])

    def test_updates_existing_memory(self):
        existing = memory.add_memory("I have 2K LinkedIn followers.", return_result=True)
        corrected = memory.get_explicit_memory(
            "I have 2.5 followers on linked in. Remember this."
        )

        result = memory.add_memory(corrected, return_result=True)

        self.assertEqual(result["action"], "UPDATE")
        self.assertEqual(result["memory"]["id"], existing["memory"]["id"])
        self.assertEqual(result["memory"]["memory"], "I have 2.5 followers on linked in")
        self.assertEqual(len(memory.get_memories()), 1)

    def test_forgets_memory_referenced_by_recent_context(self):
        memory.add_memory("I have 2K LinkedIn followers.")
        context = (
            "How many followers do I have on LinkedIn?\n"
            "You have 2K followers on LinkedIn."
        )

        removed = memory.forget_memory("", context=context)

        self.assertEqual(memory.get_forget_request("forget it."), "")
        self.assertEqual(removed, 1)
        self.assertEqual(memory.get_memories(), [])

    def test_numeric_correction_preserves_unit(self):
        memory.add_memory("I have 2K LinkedIn followers.")

        result = memory.add_memory(
            "I have 2.5K LinkedIn followers.", return_result=True
        )

        self.assertEqual(result["action"], "UPDATE")
        self.assertEqual(result["memory"]["memory"], "I have 2.5K LinkedIn followers.")
        self.assertEqual(len(memory.get_memories()), 1)

    def test_correction_collapses_conflicting_duplicates(self):
        memory.save_memory([
            memory._prepare_incoming("I have 2K LinkedIn followers."),
            memory._prepare_incoming("I have 2.5K LinkedIn followers."),
        ])

        result = memory.add_memory(
            "I have 3K LinkedIn followers.", return_result=True
        )

        self.assertEqual(result["action"], "UPDATE")
        self.assertEqual(len(memory.get_memories()), 1)
        self.assertEqual(memory.get_memories()[0]["memory"], "I have 3K LinkedIn followers.")


if __name__ == "__main__":
    unittest.main()