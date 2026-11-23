from __future__ import annotations

from apps.memory.models import DomainContext, UserPreferences

_VALID_CONTEXTS = {c.value for c in DomainContext}


def get_user_preferences(telegram_user_id: int) -> UserPreferences:
    prefs, _ = UserPreferences.objects.get_or_create(telegram_user_id=telegram_user_id)
    return prefs


def format_preferences_message(prefs: UserPreferences) -> str:
    ctx = prefs.default_context or "(padrão: pessoal)"
    feedback = "ativado" if prefs.feedback_enabled else "desativado"
    return (
        "⚙️ **Preferências**\n"
        f"• Contexto padrão: {ctx}\n"
        f"• Feedback 👍/👎: {feedback}\n\n"
        "Ajuste: `/prefs contexto theo` · `/prefs feedback off`"
    )


def apply_preference_update(telegram_user_id: int, args: list[str]) -> str:
    if not args:
        return format_preferences_message(get_user_preferences(telegram_user_id))

    prefs = get_user_preferences(telegram_user_id)
    key = args[0].lower()
    rest = args[1:]

    if key in ("contexto", "context"):
        if not rest:
            return "Informe o contexto: casa, theo, trabalho ou pessoal."
        value = rest[0].lower()
        if value not in _VALID_CONTEXTS:
            return f"Contexto inválido. Use: {', '.join(sorted(_VALID_CONTEXTS))}"
        prefs.default_context = value
        prefs.save(update_fields=["default_context", "updated_at"])
        return f"Contexto padrão definido: {value}"

    if key == "feedback":
        if not rest:
            return "Use `/prefs feedback on` ou `off`."
        flag = rest[0].lower()
        if flag in ("on", "sim", "1", "ativar", "ativo"):
            prefs.feedback_enabled = True
        elif flag in ("off", "não", "nao", "0", "desativar", "inativo"):
            prefs.feedback_enabled = False
        else:
            return "Use `on` ou `off`."
        prefs.save(update_fields=["feedback_enabled", "updated_at"])
        state = "ativado" if prefs.feedback_enabled else "desativado"
        return f"Feedback {state}."

    return format_preferences_message(prefs)


def default_context_for_user(telegram_user_id: int | None) -> str | None:
    if telegram_user_id is None:
        return None
    prefs = UserPreferences.objects.filter(telegram_user_id=telegram_user_id).first()
    if prefs and prefs.default_context:
        return prefs.default_context
    return None


def feedback_enabled_for_user(telegram_user_id: int | None) -> bool:
    if telegram_user_id is None:
        return True
    prefs = UserPreferences.objects.filter(telegram_user_id=telegram_user_id).first()
    if prefs is None:
        return True
    return prefs.feedback_enabled