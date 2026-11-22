from __future__ import annotations

from dataclasses import dataclass

from apps.ai.schemas import AgentPlan

# Valores persistidos em InteractionLog.llm_outcome
LLM_OK = "ok"
LLM_FALLBACK = "fallback"
LLM_PARSE_ERROR = "parse_error"
LLM_GROQ_RATE_LIMIT = "groq_rate_limit"
LLM_GROQ_API = "groq_api"
LLM_NO_KEY = "no_key"
LLM_EMPTY_INPUT = "empty_input"

OUTCOME_CHOICES = [
    (LLM_OK, "OK"),
    (LLM_FALLBACK, "Fallback genérico"),
    (LLM_PARSE_ERROR, "JSON / validação inválida"),
    (LLM_GROQ_RATE_LIMIT, "Groq rate limit"),
    (LLM_GROQ_API, "Groq API / rede"),
    (LLM_NO_KEY, "GROQ_API_KEY ausente"),
    (LLM_EMPTY_INPUT, "Entrada vazia"),
]


@dataclass(frozen=True)
class LlmParseResult:
    plan: AgentPlan
    outcome: str