from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def pending_confirmation_keyboard(
    pending_id: int,
    *,
    show_shopping_list: bool = True,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton("Sim", callback_data=f"pc:{pending_id}:y"),
            InlineKeyboardButton("Não", callback_data=f"pc:{pending_id}:n"),
        ],
    ]
    if show_shopping_list:
        rows.append(
            [InlineKeyboardButton("Ver lista de mercado", callback_data="pc:list:shopping")]
        )
    return InlineKeyboardMarkup(rows)


def feedback_keyboard(log_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👍", callback_data=f"fb:{log_id}:up"),
                InlineKeyboardButton("👎", callback_data=f"fb:{log_id}:down"),
            ],
        ]
    )