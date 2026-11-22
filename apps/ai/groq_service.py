from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from groq import APIConnectionError, APIStatusError, Groq, RateLimitError

from apps.ai.llm_outcomes import (
    LLM_EMPTY_INPUT,
    LLM_FALLBACK,
    LLM_GROQ_API,
    LLM_GROQ_RATE_LIMIT,
    LLM_NO_KEY,
    LLM_OK,
    LLM_PARSE_ERROR,
    LlmParseResult,
)
from apps.ai.schemas import AgentPlan

logger = logging.getLogger(__name__)

TZ = ZoneInfo("America/Sao_Paulo")
WEEKDAYS_PT = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


def _llm_model() -> str:
    return settings.GROQ_LLM_MODEL or "openai/gpt-oss-120b"


def _whisper_model() -> str:
    return settings.GROQ_WHISPER_MODEL or "whisper-large-v3-turbo"


FALLBACK_PLAN = AgentPlan(
    actions=[],
    reply_hint="Não consegui processar agora. Tente novamente em instantes.",
)


def _client() -> Groq:
    return Groq(api_key=settings.GROQ_API_KEY)


def _fallback(outcome: str, plan: AgentPlan | None = None) -> LlmParseResult:
    logger.info("llm_parse outcome=%s", outcome)
    return LlmParseResult(plan=plan or FALLBACK_PLAN, outcome=outcome)


def _now_context_line() -> str:
    now = datetime.now(TZ)
    weekday = WEEKDAYS_PT[now.weekday()]
    return (
        f"Referência temporal (America/Sao_Paulo): "
        f"{weekday}, {now:%d/%m/%Y %H:%M} (offset {now:%z}). "
        f"Converta expressões relativas (amanhã, quinta, semana que vem) para ISO "
        f"em start_at ou due_date usando esse fuso."
    )


def _system_prompt() -> str:
    schema_hint = json.dumps(AgentPlan.model_json_schema(), ensure_ascii=False)
    action_types = ", ".join(
        [
            "add_shopping",
            "mark_shopping_bought",
            "remove_shopping",
            "dedupe_shopping",
            "list_shopping",
            "add_task",
            "complete_task",
            "delete_task",
            "clear_tasks",
            "list_tasks",
            "add_event",
            "delete_event",
            "clear_events",
            "list_events",
            "add_note",
            "search_notes",
            "summarize",
        ]
    )
    return f"""Você é o roteador de um assistente pessoal em português do Brasil.
O usuário é o dono único do sistema: você TEM permissão total para criar, alterar e EXCLUIR dados.
Nunca recuse por "falta de permissão"; traduza o pedido em ações estruturadas.
Analise a mensagem e retorne APENAS um objeto JSON válido (sem markdown).

{_now_context_line()}

Regras:
- Extraia uma ou mais ações em "actions". Cada ação tem "type" obrigatório.
- Campos opcionais por tipo:
  * add_shopping: item_name, quantity (texto opcional, nunca negativo ou "(-2)")
  * mark_shopping_bought: item_name
  * remove_shopping: item_name (apaga da lista pendente; use para "tirar/remover/excluir item X")
  * dedupe_shopping: sem campos (remove duplicatas na lista pendente, mantém 1 por nome)
  * list_shopping: sem campos
  * add_task: title, context, due_date
  * complete_task: title (marca concluída; NÃO use para apagar)
  * delete_task: title (apaga UMA ou mais que casem no título)
  * clear_tasks: sem title; opcional context — apaga TODAS as tarefas pendentes
    (use para "remover todas as pendentes", "limpar lista de tarefas", etc.)
  * list_tasks: context (opcional)
  * add_event: title, context, start_at
  * delete_event: title (apaga compromisso(s) que casem no título)
  * clear_events: sem title; opcional context — apaga TODOS os compromissos futuros
  * list_events: sem campos
- Resumo geral / "o que temos registrado": use UMA ação summarize (não search_notes).
- "pendências" = tarefas pendentes (clear_tasks). "compromissos" = eventos (clear_events).
- Pedidos combinados: use várias ações (ex.: clear_events + clear_tasks).
  * add_note: content, context
  * search_notes: query (obrigatório; NUNCA use sem query)
  * summarize: sem campos — visão geral: mercado + tarefas pendentes + compromissos + últimas notas
- Mercado: não duplique itens já pendentes — prefira dedupe_shopping ou omita add_shopping repetido.
- Duplicatas no mercado: use dedupe_shopping (NUNCA invente add_shopping com quantidade negativa).
- Remover/apagar/excluir tarefa: delete_task. Concluir/marcar feito: complete_task.
- Inferir "context" quando óbvio (Theo -> theo, mercado/casa -> casa).
- "reply_hint": confirmação curta; nunca mencione falta de permissão.
- Tipos permitidos: {action_types}.

JSON Schema de referência:
{schema_hint}"""


def transcribe_audio(file_path: str) -> str:
    """Transcreve áudio via Groq Whisper (pt-BR)."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo de áudio não encontrado: {file_path}")
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY não configurada")

    client = _client()
    try:
        with path.open("rb") as audio_file:
            result = client.audio.transcriptions.create(
                file=audio_file,
                model=_whisper_model(),
                language="pt",
            )
        text = (result.text or "").strip()
        if not text:
            raise ValueError("Transcrição vazia")
        return text
    except (APIConnectionError, RateLimitError, APIStatusError, ValueError) as exc:
        logger.exception("Falha na transcrição Groq: %s", exc)
        raise


def parse_user_message(text: str) -> LlmParseResult:
    """Envia texto ao LLM Groq e valida a saída como AgentPlan."""
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY ausente; retornando plano fallback")
        return _fallback(
            LLM_NO_KEY,
            FALLBACK_PLAN.model_copy(
                update={"reply_hint": "Configure GROQ_API_KEY para usar a IA."}
            ),
        )

    trimmed = text.strip()
    if not trimmed:
        return LlmParseResult(
            plan=AgentPlan(
                actions=[],
                reply_hint="Não recebi texto para processar.",
            ),
            outcome=LLM_EMPTY_INPUT,
        )

    client = _client()
    try:
        completion = client.chat.completions.create(
            model=_llm_model(),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": trimmed},
            ],
            temperature=0.2,
        )
        raw = (completion.choices[0].message.content or "").strip()
        if not raw:
            logger.warning("Groq retornou JSON vazio")
            return _fallback(LLM_FALLBACK)

        payload = json.loads(raw)
        if "actions" not in payload:
            actions_raw = payload.get("action") or payload.get("items")
            if isinstance(actions_raw, list):
                payload = {"actions": actions_raw, "reply_hint": payload.get("reply_hint", "")}
            else:
                payload.setdefault("actions", [])

        plan = AgentPlan.model_validate(payload)
        if not plan.actions and not plan.reply_hint:
            return _fallback(
                LLM_FALLBACK,
                plan.model_copy(update={"reply_hint": FALLBACK_PLAN.reply_hint}),
            )
        return LlmParseResult(plan=plan, outcome=LLM_OK)
    except json.JSONDecodeError as exc:
        logger.exception("JSON inválido da Groq: %s", exc)
        return _fallback(LLM_PARSE_ERROR)
    except RateLimitError as exc:
        logger.exception("Groq rate limit: %s", exc)
        return _fallback(LLM_GROQ_RATE_LIMIT)
    except (APIConnectionError, APIStatusError) as exc:
        logger.exception("Erro de API Groq: %s", exc)
        return _fallback(LLM_GROQ_API)
    except Exception as exc:
        logger.exception("Erro ao parsear plano: %s", exc)
        return _fallback(LLM_FALLBACK)