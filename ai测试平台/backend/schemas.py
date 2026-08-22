# -*- coding: utf-8 -*-
"""接口数据模型（Pydantic）。"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Env(BaseModel):
    name: str = "默认环境"
    base_url: str = ""
    headers: Dict[str, str] = Field(default_factory=dict)
    variables: Dict[str, str] = Field(default_factory=dict)


class Settings(BaseModel):
    ai_base_url: str = "https://api.deepseek.com/v1"
    ai_api_key: str = ""
    ai_model: str = "deepseek-chat"
    ai_temperature: float = 0.2
    ai_timeout: int = 120
    mock_mode: bool = True
    run_timeout: int = 30
    verify_ssl: bool = True
    auto_cleanup: bool = False
    envs: List[Env] = Field(default_factory=lambda: [Env()])


class Assertion(BaseModel):
    type: str = "status_code"  # status_code / json / text / time
    path: str = ""
    operator: str = "=="  # == != > >= < <= contains not_contains exists not_exists type regex
    expected: str = "200"


class ExtractRule(BaseModel):
    name: str = ""
    path: str = ""


class CleanupRule(BaseModel):
    method: str = "DELETE"
    url: str = ""


class CaseIn(BaseModel):
    operation_id: Optional[int] = None
    name: str = ""
    module: str = "默认"
    method: str = "GET"
    url: str = ""
    env: str = "默认环境"
    headers: Dict[str, str] = Field(default_factory=dict)
    query: Dict[str, str] = Field(default_factory=dict)
    path_params: Dict[str, str] = Field(default_factory=dict)
    body: Any = None
    body_type: str = "json"  # json / form / raw
    expected_status: int = 200
    assertions: List[Assertion] = Field(default_factory=list)
    description: str = ""
    priority: str = "P2"
    enabled: bool = True
    source: str = "manual"
    setup_case_id: Optional[int] = None
    extract_rules: List[ExtractRule] = Field(default_factory=list)
    cleanup_rules: List[CleanupRule] = Field(default_factory=list)


class AiGenerateIn(BaseModel):
    operation_ids: List[int] = Field(default_factory=list)
    mode: str = "normal"  # normal / param / business / all / free
    extra_prompt: str = ""
    free_text: str = ""
    env: str = "默认环境"


class RunIn(BaseModel):
    name: str = ""
    env: str = ""
    case_ids: List[int] = Field(default_factory=list)
