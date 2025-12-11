"""
Configuration dataclasses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class VLMConfig:
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None

    @classmethod
    def from_env(cls) -> "VLMConfig":
        return cls(
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name=os.getenv("OPENAI_MODEL"),
        )

    def is_valid(self) -> bool:
        return bool(self.base_url and self.model_name)


@dataclass
class LLMConfig:
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    api_version: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            model_name=os.getenv("LLM_MODEL_NAME"),
            api_key=os.getenv("LLM_KEY"),
            api_base=os.getenv("LLM_API"),
            api_version=os.getenv("LLM_version"),
        )

    def is_valid(self) -> bool:
        return bool(self.model_name and self.api_key and self.api_base)


@dataclass
class Config:
    vlm: VLMConfig
    llm: LLMConfig

    @classmethod
    def from_env(cls) -> "Config":
        return cls(vlm=VLMConfig.from_env(), llm=LLMConfig.from_env())


def load_config() -> Config:
    return Config.from_env()

