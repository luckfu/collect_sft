import unittest

from stream_merger import AnthropicMessagesMerger, OpenAIChatMerger


class StreamMergerTests(unittest.TestCase):
    def test_openai_merges_reasoning_text_and_tool_arguments(self):
        merger = OpenAIChatMerger()
        merger.feed({"id": "chat-1", "model": "m", "choices": [{"delta": {
            "role": "assistant", "reasoning_content": "think ",
            "tool_calls": [{"index": 0, "id": "call-1", "function": {"name": "lookup", "arguments": "{\"q\":"}}],
        }}]})
        merger.feed({"choices": [{"delta": {
            "content": "done", "tool_calls": [{"index": 0, "function": {"arguments": "\"x\"}"}}],
        }, "finish_reason": "tool_calls"}], "usage": {"total_tokens": 9}})

        result = merger.result()
        message = result["choices"][0]["message"]
        self.assertEqual(message["content"], "done")
        self.assertEqual(message["reasoning_content"], "think ")
        self.assertEqual(message["tool_calls"][0]["function"]["arguments"], '{"q":"x"}')
        self.assertEqual(result["choices"][0]["finish_reason"], "tool_calls")

    def test_anthropic_preserves_thinking_signature_and_tool_input(self):
        merger = AnthropicMessagesMerger()
        events = [
            {"type": "message_start", "message": {"id": "msg-1", "role": "assistant", "model": "m", "usage": {"input_tokens": 2}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "why"}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "sig"}},
            {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "tool-1", "name": "lookup"}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"q":"x"}'}},
            {"type": "content_block_stop", "index": 1},
            {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 4}},
        ]
        for event in events:
            merger.feed(event)

        result = merger.result()
        self.assertEqual(result["content"][0]["thinking"], "why")
        self.assertEqual(result["content"][0]["signature"], "sig")
        self.assertEqual(result["content"][1]["input"], {"q": "x"})
        self.assertEqual(result["usage"], {"input_tokens": 2, "output_tokens": 4})


if __name__ == "__main__":
    unittest.main()
