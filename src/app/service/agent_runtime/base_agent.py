from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from src.app.service.agent_runtime.context import truncate_context
from src.domain.entity import AgentRunRecord
from src.infra.adapter.mcp import MCPToolRegistry, parse_json_action
from src.infra.repo.mem import MemUnitOfWork


class ChatModel(Protocol):
    def chat(self, messages: list[dict[str, str]]) -> str: ...


@dataclass(slots=True)
class BaseAgentResult:
    success: bool
    final_answer: str = ""
    steps_used: int = 0
    stopped_reason: str = ""
    traces: list[AgentRunRecord] = field(default_factory=list)


class BaseAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        model: ChatModel,
        registry: MCPToolRegistry,
        uow: MemUnitOfWork,
        max_steps: int = 6,
        max_context_chars: int = 12000,
        tool_retry_times: int = 1,
    ) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.registry = registry
        self.uow = uow
        self.max_steps = max_steps
        self.max_context_chars = max_context_chars
        self.tool_retry_times = tool_retry_times

    def run(
        self,
        task_id: str,
        user_input: str,
        allowed_tools: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> BaseAgentResult:
        allowed_tools = allowed_tools or [tool["name"] for tool in self.registry.list_specs()]
        context = context or {}
        traces: list[AgentRunRecord] = []
        observations: list[str] = []

        for step in range(1, self.max_steps + 1):
            prompt = self._build_prompt(user_input, allowed_tools, context, observations)
            raw_output = self.model.chat(
                [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ]
            )
            try:
                action = parse_json_action(raw_output)
            except Exception as exc:  # noqa: BLE001
                record = self._record(
                    task_id=task_id,
                    thought="模型未输出合法 JSON Action。",
                    action="parse_json_action",
                    observation=f"解析失败: {exc}",
                    metadata={"raw_output": raw_output[:1000], "step": step},
                )
                traces.append(record)
                return BaseAgentResult(
                    success=False,
                    steps_used=step,
                    stopped_reason="invalid_json_action",
                    traces=traces,
                )

            thought = str(action["思考"])
            tool_name = str(action["动作"])
            arguments = action["参数"]
            if tool_name in {"final_answer", "finish"}:
                final_answer = str(arguments.get("answer", ""))
                record = self._record(task_id, thought, tool_name, final_answer, {"step": step})
                traces.append(record)
                return BaseAgentResult(True, final_answer=final_answer, steps_used=step, stopped_reason="finished", traces=traces)

            if tool_name not in allowed_tools:
                observation = f"工具 {tool_name} 不在当前 Agent 白名单内。"
                record = self._record(task_id, thought, tool_name, observation, {"step": step})
                traces.append(record)
                return BaseAgentResult(False, steps_used=step, stopped_reason="tool_not_allowed", traces=traces)

            result = self._call_tool_with_retry(tool_name, arguments, task_id)
            observation = str(result)
            observations.append(f"{tool_name}: {observation[:1000]}")
            tool_call_id = self._latest_tool_call_id(task_id)
            record = self._record(
                task_id,
                thought,
                tool_name,
                observation[:1000],
                {"step": step, "tool_call_id": tool_call_id},
                tool_call_id=tool_call_id,
            )
            traces.append(record)

        return BaseAgentResult(False, steps_used=self.max_steps, stopped_reason="max_steps_reached", traces=traces)

    def _call_tool_with_retry(self, tool_name: str, arguments: dict[str, Any], task_id: str) -> dict[str, Any]:
        attempts = self.tool_retry_times + 1
        last_result: dict[str, Any] = {}
        for attempt in range(attempts):
            result = self.registry.call(tool_name, arguments, task_id=task_id).to_dict()
            last_result = result
            if result["success"] or result.get("error_code") == "INVALID_ARGUMENTS":
                return result
            if attempt < attempts - 1:
                continue
        return last_result

    def _build_prompt(
        self,
        user_input: str,
        allowed_tools: list[str],
        context: dict[str, Any],
        observations: list[str],
    ) -> str:
        tool_specs = [tool for tool in self.registry.list_specs() if tool["name"] in allowed_tools]
        prompt = (
            "你是受控 ReAct Agent。每次只能输出 JSON Action，格式为：\n"
            '{"思考":"...","动作":"工具名或final_answer","参数":{...}}\n'
            "禁止输出买卖建议、目标价、收益承诺或涨跌预测。\n\n"
            f"可用工具：{tool_specs}\n\n"
            f"任务输入：{user_input}\n\n"
            f"上下文：{context}\n\n"
            f"历史观察：{observations}\n"
        )
        return truncate_context(prompt, self.max_context_chars)

    def _record(
        self,
        task_id: str,
        thought: str,
        action: str,
        observation: str,
        metadata: dict[str, Any],
        tool_call_id: str = "",
    ) -> AgentRunRecord:
        record = AgentRunRecord(
            task_id=task_id,
            agent_name=self.name,
            thought=thought,
            action=action,
            observation=observation,
            tool_call_id=tool_call_id,
            metadata=metadata,
        )
        return self.uow.agent_runs.save(record)

    def _latest_tool_call_id(self, task_id: str) -> str:
        records = self.uow.tool_calls.list_by_task(task_id)
        return records[-1].call_id if records else ""
