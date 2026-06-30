from __future__ import annotations

from typing import Any

from config.settings import ModelSettings
from src.app.service.agent_runtime import BaseAgent
from src.infra.adapter.mcp import MCPToolRegistry
from src.infra.external.ollama_client import OllamaClient
from src.infra.repo.mem import MemUnitOfWork


class AgentRuntimeService:
    def __init__(
        self,
        model_settings: ModelSettings,
        ollama: OllamaClient,
        registry: MCPToolRegistry,
        uow: MemUnitOfWork,
    ) -> None:
        self.model_settings = model_settings
        self.ollama = ollama
        self.registry = registry
        self.uow = uow

    def model_health(self) -> dict[str, Any]:
        return self.ollama.health()

    def create_base_agent(self, name: str, system_prompt: str) -> BaseAgent:
        return BaseAgent(
            name=name,
            system_prompt=system_prompt,
            model=self.ollama,
            registry=self.registry,
            uow=self.uow,
            max_steps=self.model_settings.max_agent_steps,
            max_context_chars=self.model_settings.max_context_chars,
            tool_retry_times=self.model_settings.tool_retry_times,
        )
