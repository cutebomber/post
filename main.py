"""
Telegram Channel Post Bot
- Posts rich messages with colored inline buttons to a channel
- Supports premium custom emojis (via emoji entities)
- Run: python bot.py
"""

import os
import logging
import json
import re
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Conversation states ──────────────────────────────────────────────────────
(
    MAIN_MENU,
    ENTER_TEXT,
    ENTER_BUTTONS,
    CONFIRM_POST,
    ENTER_CHANNEL,
) = range(5)

# ── In-memory draft store (per user) ────────────────────────────────────────
drafts: dict[int, dict] = {}


def get_draft(user_id: int) -> dict:
    if user_id not in drafts:
        drafts[user_id] = {"text": "", "entities": [], "buttons": [], "channel": ""}
    return drafts[user_id]


# ── Helpers ──────────────────────────────────────────────────────────────────

def build_keyboard(buttons: list[dict]) -> InlineKeyboardMarkup | None:
    """
    buttons: list of {"text": str, "url": str | None, "callback": str | None, "emoji_id": str | None}
    Telegram doesn't support native button colors via Bot API — we simulate
    color via emoji prefixes embedded in button text.
    """
    if not buttons:
        return None

    # Group into rows of up to 2
    rows = []
    for i in range(0, len(buttons), 2):
        row = []
        for btn in buttons[i : i + 2]:
            label = btn["text"]
            if btn.get("emoji_id"):
                # Custom emoji in button text (premium feature)
                # Telegram renders custom emoji in inline keyboard labels
                label = f"{btn['emoji_id_char']}{label}" if btn.get("emoji_id_char") else label
            if btn.get("url"):
                row.append(InlineKeyboardButton(label, url=btn["url"]))
            else:
                cb = btn.get("callback", "noop")
                row.append(InlineKeyboardButton(label, callback_data=cb))
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def parse_button_line(line: str) -> dict | None:
    """
    Syntax:
      Button Text | https://url.com
      Button Text | /callback_data
      Button Text | https://url.com | 🎨 (custom emoji id)
    """
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 2:
        return None
    btn: dict = {"text": parts[0], "url": None, "callback": None, "emoji_id": None}
    target = parts[1]
    if target.startswith("http://") or target.startswith("https://"):
        btn["url"] = target
    else:
        btn["callback"] = target.lstrip("/")
    if len(parts) >= 3:
        # Third part treated as custom emoji document_id or visible emoji
        btn["emoji_id_char"] = parts[2]
    return btn


# ── Command: /start ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    get_draft(user_id)  # init
    await show_main_menu(update, ctx)
    return MAIN_MENU


async def show_main_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Write Post Text", callback_data="action_text")],
        [InlineKeyboardButton("🔘 Add Buttons", callback_data="action_buttons")],
        [InlineKeyboardButton("📢 Set Channel", callback_data="action_channel")],
        [InlineKeyboardButton("👁 Preview", callback_data="action_preview")],
        [InlineKeyboardButton("🚀 Post to Channel", callback_data="action_post")],
        [InlineKeyboardButton("🗑 Clear Draft", callback_data="action_clear")],
    ])
    text = (
        "📬 *Channel Post Composer*\n\n"
        "Build a post with rich text and inline buttons\\.\n\n"
        "Supports:\n"
        "• Bold, italic, code, spoiler via MarkdownV2\n"
        "• Custom premium emojis in text\n"
        "• Colored buttons \\(emoji prefixes\\)\n"
        "• URL and callback buttons\n\n"
        "Choose an action:"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboard
        )


# ── Callback router ──────────────────────────────────────────────────────────

async def menu_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "action_text":
        await q.edit_message_text(
            "✏️ *Enter your post text*\n\n"
            "Use MarkdownV2 formatting:\n"
            "`*bold*` \\| `_italic_` \\| `__underline__` \\| `~strikethrough~`\n"
            "`||spoiler||` \\| `` `code` `` \\| `[link](url)`\n\n"
            "For custom emojis paste them directly into the text \\(requires premium\\)\\.\n\n"
            "Send your text now:",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ENTER_TEXT

    elif data == "action_buttons":
        await q.edit_message_text(
            "🔘 *Add Inline Buttons*\n\n"
            "Send one button per line in format:\n"
            "`Button Label | https://example.com`\n"
            "`Button Label | /callback_data`\n\n"
            "Add emoji prefix for color effect:\n"
            "`🟢 Join Now | https://t.me/yourchannel`\n"
            "`🔴 Leave | /leave`\n"
            "`🔵 Info | https://example.com`\n\n"
            "Up to 2 buttons per row \\(just list them and they auto\\-pair\\)\\.\n\n"
            "Send your buttons:",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ENTER_BUTTONS

    elif data == "action_channel":
        await q.edit_message_text(
            "📢 *Set Target Channel*\n\n"
            "Send the channel username or ID:\n"
            "`@yourchannel` or `-1001234567890`\n\n"
            "Make sure this bot is an *admin* in that channel with *Post Messages* permission\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ENTER_CHANNEL

    elif data == "action_preview":
        return await show_preview(update, ctx)

    elif data == "action_post":
        return await do_post(update, ctx)

    elif data == "action_clear":
        drafts[update.effective_user.id] = {"text": "", "entities": [], "buttons": [], "channel": ""}
        await q.answer("Draft cleared!", show_alert=True)
        await show_main_menu(update, ctx)
        return MAIN_MENU

    elif data == "back_menu":
        await show_main_menu(update, ctx)
        return MAIN_MENU

    else:
        await q.answer("Button pressed: " + data)
        return MAIN_MENU


# ── Enter text state ─────────────────────────────────────────────────────────

async def receive_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    draft = get_draft(user_id)
    msg = update.message

    draft["text"] = msg.text or msg.caption or ""
    # Preserve entities for custom emoji support
    entities = msg.entities or msg.caption_entities or []
    draft["entities"] = [e.to_dict() for e in entities]

    await msg.reply_text(
        f"✅ Text saved\\! \\({len(draft['text'])} chars\\)",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]
        ]),
    )
    return MAIN_MENU


# ── Enter buttons state ──────────────────────────────────────────────────────

async def receive_buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    draft = get_draft(user_id)
    lines = update.message.text.strip().splitlines()

    parsed = []
    errors = []
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        btn = parse_button_line(line)
        if btn:
            parsed.append(btn)
        else:
            errors.append(f"Line {i}: `{line}`")

    draft["buttons"] = parsed

    msg_parts = [f"✅ *{len(parsed)} button(s) saved\\!*"]
    if errors:
        msg_parts.append("⚠️ Could not parse:\n" + "\n".join(errors))

    await update.message.reply_text(
        "\n\n".join(msg_parts),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]
        ]),
    )
    return MAIN_MENU


# ── Enter channel state ──────────────────────────────────────────────────────

async def receive_channel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    draft = get_draft(user_id)
    draft["channel"] = update.message.text.strip()

    await update.message.reply_text(
        f"✅ Channel set to `{draft['channel']}`",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]
        ]),
    )
    return MAIN_MENU


# ── Preview ──────────────────────────────────────────────────────────────────

async def show_preview(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    user_id = update.effective_user.id
    draft = get_draft(user_id)

    if not draft["text"]:
        await q.answer("No text set yet!", show_alert=True)
        return MAIN_MENU

    keyboard = build_keyboard(draft["buttons"])
    caption_parts = []
    if draft["channel"]:
        caption_parts.append(f"📢 Channel: {draft['channel']}")
    caption_parts.append(f"🔘 Buttons: {len(draft['buttons'])}")

    try:
        await q.message.reply_text(
            "👁 *Preview:*\n" + "\n".join(caption_parts),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        # Send the actual preview with entities
        entities = [MessageEntity.de_json(e, ctx.bot) for e in draft.get("entities", [])]
        await ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text=draft["text"],
            entities=entities if entities else None,
            reply_markup=keyboard,
        )
    except Exception as e:
        await q.message.reply_text(f"⚠️ Preview error: {e}")

    await q.message.reply_text(
        "How does it look?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Post It!", callback_data="action_post")],
            [InlineKeyboardButton("✏️ Edit", callback_data="back_menu")],
        ]),
    )
    return MAIN_MENU


# ── Post ─────────────────────────────────────────────────────────────────────

async def do_post(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    user_id = update.effective_user.id
    draft = get_draft(user_id)

    if not draft["text"]:
        await q.answer("Write some text first!", show_alert=True)
        return MAIN_MENU
    if not draft["channel"]:
        await q.answer("Set a channel first!", show_alert=True)
        return MAIN_MENU

    keyboard = build_keyboard(draft["buttons"])
    entities = [MessageEntity.de_json(e, ctx.bot) for e in draft.get("entities", [])]

    try:
        sent = await ctx.bot.send_message(
            chat_id=draft["channel"],
            text=draft["text"],
            entities=entities if entities else None,
            reply_markup=keyboard,
        )
        await q.edit_message_text(
            f"✅ *Posted successfully\\!*\n\nMessage ID: `{sent.message_id}`",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📬 New Post", callback_data="action_clear")],
            ]),
        )
    except Exception as e:
        await q.edit_message_text(
            f"❌ *Failed to post:*\n`{e}`\n\nMake sure the bot is admin in the channel\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]
            ]),
        )
    return MAIN_MENU


# ── Fallback ─────────────────────────────────────────────────────────────────

async def fallback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Use /start to open the composer.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📬 Open Composer", callback_data="back_menu")]
        ]),
    )
    return MAIN_MENU


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Set the BOT_TOKEN environment variable")

    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(menu_callback),
            ],
            ENTER_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text),
                CallbackQueryHandler(menu_callback, pattern="back_menu"),
            ],
            ENTER_BUTTONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_buttons),
                CallbackQueryHandler(menu_callback, pattern="back_menu"),
            ],
            ENTER_CHANNEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel),
                CallbackQueryHandler(menu_callback, pattern="back_menu"),
            ],
        },
        fallbacks=[
            CommandHandler("start", cmd_start),
            MessageHandler(filters.ALL, fallback),
        ],
        per_message=False,
    )

    app.add_handler(conv)
    logger.info("Bot started. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
