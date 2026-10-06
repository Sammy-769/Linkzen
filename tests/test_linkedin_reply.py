import unittest
from types import SimpleNamespace
from unittest.mock import patch

import assistant
from settings import DEFAULT_LINKEDIN_PROMPTS


class LinkedInReplyTests(unittest.TestCase):
    def run_tool(
        self,
        action,
        text,
        instructions="",
        images=None,
        custom_prompt=None,
        performance_data="",
    ):
        calls = {
            "messages": None,
            "page_request": None,
            "retrieval_query": None,
            "disable_thinking": None,
        }
        configured_prompts = dict(DEFAULT_LINKEDIN_PROMPTS)
        if custom_prompt is not None:
            configured_prompts[action] = custom_prompt
        configured_settings = {
            "rag_enabled": False,
            "memory_debug": False,
            "linkedin_prompts": configured_prompts,
        }

        def read_pages(request_text):
            calls["page_request"] = request_text
            if "https://" in request_text:
                return "Webpage context: reply details from the supplied link.", True
            return request_text, False

        def retrieve(query, limit=3, enabled=True):
            calls["retrieval_query"] = query
            return "", [], {"ran": False, "reason": "disabled", "candidate_count": 0}

        def generate(messages, max_tokens, on_delta=None, disable_thinking=False):
            calls["messages"] = messages
            calls["disable_thinking"] = disable_thinking
            if on_delta:
                on_delta("Draft ")
                on_delta("reply")
            return "Draft reply"

        with (
            patch.object(assistant, "get_settings", return_value=configured_settings),
            patch.object(assistant, "read_requested_pages", side_effect=read_pages),
            patch.object(assistant, "_retrieve_knowledge", side_effect=retrieve),
            patch.object(assistant, "get_relevant_memory_text", return_value=("", [])),
            patch.object(assistant, "get_memories", return_value=[]),
            patch.object(assistant, "_deepseek_answer", side_effect=generate),
        ):
            streamed = []
            result = assistant.linkedin_tool(
                action,
                text,
                on_delta=streamed.append,
                images=images,
                instructions=instructions,
                performance_data=performance_data,
            )

        return result, calls, streamed

    def test_message_and_custom_instruction_produce_streamed_reply(self):
        result, calls, streamed = self.run_tool(
            "reply_to_message",
            "Thanks for reaching out about the role.",
            "Politely decline and leave the door open.",
        )

        prompt = calls["messages"][1]["content"]
        request = calls["messages"][-1]["content"]
        self.assertEqual(result["answer"], "Draft reply")
        self.assertEqual(streamed, ["Draft ", "reply"])
        self.assertIn("ready-to-send reply", prompt)
        self.assertIn("Thanks for reaching out about the role.", request)
        self.assertIn("Politely decline and leave the door open.", request)
        self.assertNotIn("private LinkedIn direct message reply", calls["retrieval_query"])
        self.assertIn("Politely decline and leave the door open.", calls["retrieval_query"])

    def test_url_instructions_use_shared_web_reader(self):
        _, calls, _ = self.run_tool(
            "reply_to_message",
            "I received this opportunity.",
            "Read this role description before replying: https://example.com/role",
        )

        self.assertIn("https://example.com/role", calls["page_request"])
        self.assertIn("Webpage context: reply details from the supplied link.", calls["messages"][-1]["content"])

    def test_screenshot_is_passed_as_existing_image_content(self):
        screenshot = "data:image/png;base64,c2NyZWVuc2hvdA=="
        result, calls, _ = self.run_tool(
            "reply_to_message",
            "",
            "Politely ask for more details.",
            images=[screenshot],
        )

        user_content = calls["messages"][-1]["content"]
        self.assertEqual(result["answer"], "Draft reply")
        self.assertEqual(user_content[1]["image_url"]["url"], screenshot)
        self.assertIn("message is supplied in the attached screenshot", user_content[0]["text"])

    def test_action_uses_its_own_custom_prompt(self):
        custom_prompt = "Reply in two concise sentences."
        _, calls, _ = self.run_tool(
            "reply_to_message",
            "Could we schedule a call?",
            custom_prompt=custom_prompt,
        )

        self.assertEqual(calls["messages"][1]["content"], custom_prompt)

    def test_each_requested_tool_uses_its_own_custom_system_prompt(self):
        for action in ("analyze_profile", "analyze_post", "post_ideas", "create_post"):
            custom_prompt = f"Custom system prompt for {action}."
            with self.subTest(action=action):
                _, calls, _ = self.run_tool(
                    action,
                    "A sample LinkedIn request",
                    custom_prompt=custom_prompt,
                )
                self.assertEqual(calls["messages"][1]["content"], custom_prompt)

    def test_profile_url_is_loaded_into_request_context(self):
        _, calls, _ = self.run_tool(
            "analyze_profile",
            "Analyze this public profile: https://example.com/profile",
        )

        self.assertIn("https://example.com/profile", calls["page_request"])
        self.assertIn(
            "Webpage context: reply details from the supplied link.",
            calls["messages"][-1]["content"],
        )

    def test_analyze_post_keeps_context_and_metrics_separate(self):
        result, calls, _ = self.run_tool(
            "analyze_post",
            "I learned a lot while building this small project.",
            "It was aimed at people learning cloud engineering.",
            performance_data="1,200 impressions; 24 reactions; 3 comments",
        )

        prompt = calls["messages"][1]["content"]
        request = calls["messages"][-1]["content"]
        self.assertEqual(result["answer"], "Draft reply")
        self.assertIn("Critically analyse the supplied existing LinkedIn post", prompt)
        self.assertIn(
            "LinkedIn post to analyse:\nI learned a lot while building this small project.",
            request,
        )
        self.assertIn("people learning cloud engineering", request)
        self.assertIn("Performance data (optional; analyse separately", request)
        self.assertIn("1,200 impressions; 24 reactions; 3 comments", request)
        self.assertIn("feed distribution", calls["retrieval_query"])

    def test_analyze_post_url_context_is_included_in_analysis_request(self):
        _, calls, _ = self.run_tool(
            "analyze_post",
            "Analyse this post: https://example.com/post",
        )

        self.assertIn(
            "Webpage context: reply details from the supplied link.",
            calls["messages"][-1]["content"],
        )

    def test_analyze_post_does_not_require_performance_data(self):
        _, calls, _ = self.run_tool("analyze_post", "A complete existing post.")

        self.assertIn("No performance data was provided.", calls["messages"][-1]["content"])

    def test_analyze_post_requires_post_text(self):
        with self.assertRaisesRegex(ValueError, "Paste or attach the LinkedIn post"):
            assistant.linkedin_tool("analyze_post", performance_data="100 impressions")

    def test_analyze_post_accepts_screenshot_without_text(self):
        screenshot = "data:image/png;base64,c2NyZWVuc2hvdA=="
        result, calls, _ = self.run_tool(
            "analyze_post",
            "",
            images=[screenshot],
        )

        user_content = calls["messages"][-1]["content"]
        self.assertEqual(result["answer"], "Draft reply")
        self.assertIn(
            "The post is shown in the attached screenshot.",
            user_content[0]["text"],
        )
        self.assertEqual(user_content[1]["image_url"]["url"], screenshot)

    def test_analysis_tools_disable_reasoning_that_can_exhaust_answer_budget(self):
        for action in ("analyze_profile", "analyze_post", "post_ideas", "create_post"):
            with self.subTest(action=action):
                _, calls, _ = self.run_tool(action, "A sample LinkedIn request")
                self.assertTrue(calls["disable_thinking"])

        for action in ("make_comment", "reply_to_message", "ask_knowledge"):
            with self.subTest(action=action):
                _, calls, _ = self.run_tool(action, "A sample LinkedIn request")
                self.assertFalse(calls["disable_thinking"])

    def test_disabled_thinking_is_sent_in_streaming_api_request(self):
        chunk = SimpleNamespace(
            usage=None,
            choices=[
                SimpleNamespace(
                    finish_reason="stop",
                    delta=SimpleNamespace(content="Answer"),
                )
            ],
        )
        streamed = []
        with patch.object(
            assistant.client.chat.completions,
            "create",
            return_value=[chunk],
        ) as create:
            answer = assistant._deepseek_answer(
                [],
                1200,
                streamed.append,
                disable_thinking=True,
            )

        self.assertEqual(answer, "Answer")
        self.assertEqual(streamed, ["Answer"])
        self.assertEqual(
            create.call_args.kwargs["extra_body"],
            {"thinking": {"type": "disabled"}},
        )

    def test_default_deepseek_request_keeps_existing_thinking_behavior(self):
        response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Answer"))],
            usage=None,
        )
        with (
            patch.object(
                assistant.client.chat.completions,
                "create",
                return_value=response,
            ) as create,
            patch.object(assistant, "record_response_usage"),
        ):
            answer = assistant._deepseek_answer([], 800)

        self.assertEqual(answer, "Answer")
        self.assertNotIn("extra_body", create.call_args.kwargs)

    def test_profile_screenshot_without_text_gets_profile_specific_request(self):
        screenshot = "data:image/png;base64,c2NyZWVuc2hvdA=="
        _, calls, _ = self.run_tool(
            "analyze_profile",
            "",
            images=[screenshot],
        )

        self.assertIn(
            "Analyze the LinkedIn profile shown in the attached screenshot.",
            calls["messages"][-1]["content"][0]["text"],
        )

    def test_existing_linkedin_actions_remain_registered(self):
        for action in (
            "analyze_profile",
            "create_post",
            "analyze_post",
            "post_ideas",
            "make_comment",
            "ask_knowledge",
        ):
            with self.subTest(action=action):
                result, calls, _ = self.run_tool(action, "A sample LinkedIn request")
                self.assertEqual(result["answer"], "Draft reply")
                self.assertEqual(calls["messages"][1]["content"], DEFAULT_LINKEDIN_PROMPTS[action])


if __name__ == "__main__":
    unittest.main()