from __future__ import annotations

import unittest

from src.app.service.agent_runtime import BaseAgent, truncate_context
from src.domain.tool import MCPToolResult, MCPToolSpec
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.repo.mem import MemUnitOfWork


class FakeModel:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.prompts: list[list[dict[str, str]]] = []

    def chat(self, messages: list[dict[str, str]]) -> str:
        self.prompts.append(messages)
        if not self.outputs:
            return '{"思考":"结束","动作":"final_answer","参数":{"answer":"done"}}'
        return self.outputs.pop(0)


class DayFiveAgentRuntimeTest(unittest.TestCase):
    def test_context_truncation_preserves_head_and_tail(self) -> None:
        text = "A" * 100 + "B" * 100
        truncated = truncate_context(text, 80)
        self.assertLessEqual(len(truncated), 80)
        self.assertIn("context truncated", truncated)
        self.assertTrue(truncated.startswith("A"))
        self.assertTrue(truncated.endswith("B"))

    def test_base_agent_calls_tool_and_records_trace(self) -> None:
        uow = MemUnitOfWork()
        registry = MCPToolRegistry(uow)
        registry.register(
            MCPToolSpec(
                name="echo_tool",
                description="echo",
                input_schema={"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}},
                output_schema={"type": "object"},
                error_codes={},
                data_source="unit_test",
                handler=lambda args: MCPToolResult(True, {"echo": args["text"]}, "unit_test"),
            )
        )
        model = FakeModel(
            [
                '{"思考":"需要调用工具","动作":"echo_tool","参数":{"text":"hello"}}',
                '{"思考":"已经得到观察","动作":"final_answer","参数":{"answer":"完成"}}',
            ]
        )
        agent = BaseAgent("TestAgent", "system", model, registry, uow, max_steps=3, max_context_chars=2000)
        result = agent.run("task_1", "请测试", allowed_tools=["echo_tool"])
        self.assertTrue(result.success)
        self.assertEqual(result.final_answer, "完成")
        self.assertEqual(len(uow.agent_runs.list_by_task("task_1")), 2)
        self.assertEqual(len(uow.tool_calls.list_by_task("task_1")), 1)
        self.assertEqual(uow.agent_runs.list_by_task("task_1")[0].tool_call_id, uow.tool_calls.list_by_task("task_1")[0].call_id)

    def test_base_agent_retries_failed_tool(self) -> None:
        uow = MemUnitOfWork()
        registry = MCPToolRegistry(uow)
        calls = {"count": 0}

        def flaky(_args: dict) -> MCPToolResult:
            calls["count"] += 1
            if calls["count"] == 1:
                return MCPToolResult(False, {}, "unit_test", error_code="TEMP_ERROR", error_message="temporary")
            return MCPToolResult(True, {"ok": True}, "unit_test")

        registry.register(
            MCPToolSpec(
                name="flaky_tool",
                description="flaky",
                input_schema={"type": "object", "required": [], "properties": {}},
                output_schema={"type": "object"},
                error_codes={"TEMP_ERROR": "temporary"},
                data_source="unit_test",
                handler=flaky,
            )
        )
        model = FakeModel(['{"思考":"试一下","动作":"flaky_tool","参数":{}}'])
        agent = BaseAgent("RetryAgent", "system", model, registry, uow, max_steps=1, tool_retry_times=1)
        result = agent.run("task_retry", "retry", allowed_tools=["flaky_tool"])
        self.assertFalse(result.success)
        self.assertEqual(result.stopped_reason, "max_steps_reached")
        self.assertEqual(calls["count"], 2)
        self.assertEqual(len(uow.tool_calls.list_by_task("task_retry")), 2)

    def test_invalid_json_action_stops_agent(self) -> None:
        uow = MemUnitOfWork()
        registry = MCPToolRegistry(uow)
        model = FakeModel(["not json"])
        agent = BaseAgent("InvalidAgent", "system", model, registry, uow, max_steps=1)
        result = agent.run("task_invalid", "invalid", allowed_tools=[])
        self.assertFalse(result.success)
        self.assertEqual(result.stopped_reason, "invalid_json_action")
        self.assertEqual(uow.agent_runs.list_by_task("task_invalid")[0].action, "parse_json_action")

    def test_tool_not_allowed_stops_agent(self) -> None:
        uow = MemUnitOfWork()
        registry = MCPToolRegistry(uow)
        model = FakeModel(['{"思考":"调用","动作":"unknown_tool","参数":{}}'])
        agent = BaseAgent("GuardedAgent", "system", model, registry, uow, max_steps=1)
        result = agent.run("task_guard", "guard", allowed_tools=[])
        self.assertFalse(result.success)
        self.assertEqual(result.stopped_reason, "tool_not_allowed")


if __name__ == "__main__":
    unittest.main()
