import unittest

from retrieval import (
    RAG_MAX_SQUARED_L2_DISTANCE,
    legacy_index_metadata,
    memory_retrieval_query,
    retrieval_query,
    retrieve_knowledge,
)


class FakeEmbeddingModel:
    def encode(self, text):
        return [0.1, 0.2]


class FakeCollection:
    def __init__(self, rows):
        self.rows = rows
        self.query_calls = []

    def count(self):
        return len(self.rows)

    def get(self, include=None):
        return {"metadatas": [metadata for _, metadata, _ in self.rows]}

    def query(self, query_embeddings, n_results, include, where=None):
        self.query_calls.append(where)
        rows = self.rows
        if where:
            rows = [row for row in rows if row[1].get("file") == where.get("file")]
        rows = sorted(rows, key=lambda row: row[2])[:n_results]
        return {
            "documents": [[row[0] for row in rows]],
            "metadatas": [[row[1] for row in rows]],
            "distances": [[row[2] for row in rows]],
        }


class RetrievalTests(unittest.TestCase):
    def test_greeting_skips_rag_retrieval_and_sources(self):
        collection = FakeCollection([
            ("LinkedIn article excerpt", {"file": "linkedin/Guide.md"}, 0.5)
        ])

        context, sources, diagnostics = retrieve_knowledge(
            collection, FakeEmbeddingModel(), "hello"
        )

        self.assertEqual(context, "")
        self.assertEqual(sources, [])
        self.assertEqual(diagnostics["reason"], "greeting")
        self.assertEqual(collection.query_calls, [])

    def test_aws_question_returns_valid_path_filename_and_excerpt(self):
        collection = FakeCollection([
            ("Amazon RDS is a managed relational database.", {"file": "aws/What is aws.txt", "source": "What Is Aws"}, 0.92),
            ("LinkedIn writing advice", {"file": "linkedin/guide.md", "source": "Guide"}, 1.7),
        ])

        context, sources, _ = retrieve_knowledge(
            collection, FakeEmbeddingModel(), "What is Amazon RDS?"
        )

        self.assertIn("aws/What is aws.txt", context)
        self.assertEqual(sources[0]["path"], "aws/What is aws.txt")
        self.assertEqual(sources[0]["filename"], "What is aws.txt")
        self.assertIn("Amazon RDS", sources[0]["excerpt"])

    def test_unrelated_distances_are_excluded(self):
        collection = FakeCollection([
            ("Unrelated file", {"file": "linkedin/guide.md"}, RAG_MAX_SQUARED_L2_DISTANCE + 0.01)
        ])

        context, sources, _ = retrieve_knowledge(
            collection, FakeEmbeddingModel(), "What is the capital of France?"
        )

        self.assertEqual(context, "")
        self.assertEqual(sources, [])

    def test_creator_name_scopes_retrieval_to_matching_folder(self):
        collection = FakeCollection([
            ("Creator-specific profile lesson", {"file": "linkedin/Diandra Escobar/Day 1 your profile.txt"}, 1.55),
            ("General official LinkedIn guidance", {"file": "linkedin/Linkedin Official/Guide.md"}, 0.55),
        ])

        context, sources, diagnostics = retrieve_knowledge(
            collection, FakeEmbeddingModel(), "What does Diandra Escobar say about LinkedIn?"
        )

        self.assertEqual(collection.query_calls, [{"file": "linkedin/Diandra Escobar/Day 1 your profile.txt"}])
        self.assertIn("Diandra Escobar", context)
        self.assertEqual(sources[0]["path"], "linkedin/Diandra Escobar/Day 1 your profile.txt")
        self.assertEqual(diagnostics["reason"], "creator-path-match")

    def test_personal_memory_question_does_not_retrieve_knowledge(self):
        collection = FakeCollection([
            ("Reference excerpt", {"file": "aws/guide.txt"}, 0.4)
        ])

        for question in ("What do you know about me?", "So you know about me?"):
            with self.subTest(question=question):
                context, sources, diagnostics = retrieve_knowledge(
                    collection, FakeEmbeddingModel(), question
                )
                self.assertEqual(context, "")
                self.assertEqual(sources, [])
                self.assertEqual(diagnostics["reason"], "personal-memory-question")
                self.assertEqual(collection.query_calls, [])

    def test_compound_personal_and_knowledge_question_still_retrieves_knowledge(self):
        collection = FakeCollection([
            ("LinkedIn growth guidance", {"file": "linkedin/guide.md"}, 0.7)
        ])

        context, sources, diagnostics = retrieve_knowledge(
            collection,
            FakeEmbeddingModel(),
            "what do you know about me and linkedin and how can I grow my linkedin?",
        )

        self.assertIn("LinkedIn growth guidance", context)
        self.assertEqual(sources[0]["path"], "linkedin/guide.md")
        self.assertEqual(diagnostics["reason"], "vector-search")
        self.assertEqual(collection.query_calls, [None])

    def test_old_source_without_valid_path_is_not_reported(self):
        collection = FakeCollection([
            ("Excerpt", {"source": "A display title only"}, 0.3)
        ])

        context, sources, _ = retrieve_knowledge(
            collection, FakeEmbeddingModel(), "Relevant question"
        )

        self.assertEqual(context, "")
        self.assertEqual(sources, [])

    def test_retrieval_query_uses_current_request_not_assistant_history(self):
        history = [
            {"role": "user", "content": "Tell me about AWS RDS"},
            {"role": "assistant", "content": "An unrelated answer about LinkedIn"},
        ]

        self.assertEqual(retrieval_query("hello", history), "hello")
        self.assertEqual(retrieval_query("What is my name?", history), "What is my name?")
        self.assertIn("Tell me about AWS RDS", retrieval_query("What about its cost?", history))
        self.assertIn("Tell me about AWS RDS", retrieval_query("What about that?", history))
        self.assertNotIn("unrelated answer", retrieval_query("What about that?", history))

    def test_memory_query_expands_personal_intent(self):
        self.assertIn("personal profile", memory_retrieval_query("What do you know about me?"))
        self.assertIn("working towards becoming", memory_retrieval_query("What are my career goals?"))

    def test_legacy_index_chunks_map_or_remove_by_path(self):
        mapped, stale = legacy_index_metadata(
            [
                {"source": "knowledge/aws/What is aws.txt"},
                {"source": "Removed Source"},
                {"file": "aws/Current.txt", "source": "Current"},
            ],
            {"aws/What is aws.txt": {"source": "What Is Aws"}},
            {"aws/What is aws.txt"},
        )

        self.assertEqual(mapped, {"aws/What is aws.txt": {"knowledge/aws/What is aws.txt"}})
        self.assertEqual(stale, {"Removed Source"})


if __name__ == "__main__":
    unittest.main()