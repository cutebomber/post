"""
Telegram Channel Poster Bot
============================
Configure a post with colored inline buttons via a menu, then post to your channel.

Setup:
  pip install python-telegram-bot --upgrade

Usage:
  1. Set BOT_TOKEN and CHANNEL_ID below
  2. Run: python channel_poster_bot.py
  3. Open your bot in Telegram and send /start
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ──────────────────────────────────────────────
#  CONFIGURATION  ← Edit these two lines
# ──────────────────────────────────────────────
BOT_TOKEN  = "8651990559:AAHk3DToBDJCgz57OJf88AtqcLLiS-S2myk"       # from @BotFather
CHANNEL_ID = "@chillflames"    # e.g. "@mychannel" or -1001234567890
# ──────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)

# ConversationHandler states
(
    MAIN_MENU,
    TYPING_POST_TEXT,
    TYPING_BUTTON_LABEL,
    TYPING_BUTTON_URL,
    CHOOSING_BUTTON_COLOR,
    CHOOSING_BUTTON_ROW,
) = range(6)

# ─── Helpers ───────────────────────────────────

def get_session(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Return (or init) the user's draft session."""
    if "draft" not in context.user_data:
        context.user_data["draft"] = {
            "text": "✏️ Write your message here...",
            "buttons": [],          # list of {label, url, style, row}
            "parse_mode": "HTML",
        }
    return context.user_data["draft"]

def style_emoji(style: str) -> str:
    return {"primary": "🔵", "success": "🟢", "danger": "🔴", "": "⚪"}.get(style, "⚪")

def build_preview_markup(draft: dict) -> InlineKeyboardMarkup:
    """Build the actual channel post markup from draft buttons."""
    rows: dict[int, list] = {}
    for btn in draft["buttons"]:
        r = btn.get("row", 0)
        rows.setdefault(r, []).append(
            InlineKeyboardButton(
                text=btn["label"],
                url=btn["url"],
                style=btn.get("style") or None,
            )
        )
    keyboard = [rows[r] for r in sorted(rows)]
    return InlineKeyboardMarkup(keyboard) if keyboard else None

def build_main_menu(draft: dict) -> InlineKeyboardMarkup:
    btns = draft["buttons"]
    btn_count = len(btns)
    btn_summary = f"  ({btn_count} button{'s' if btn_count != 1 else ''})" if btns else ""

    keyboard = [
        [InlineKeyboardButton(f"📝  Set Post Text", callback_data="set_text")],
        [InlineKeyboardButton(f"➕  Add Button{btn_summary}", callback_data="add_button")],
    ]
    if btns:
        keyboard.append([InlineKeyboardButton("🗑️  Remove Last Button", callback_data="remove_last")])
        keyboard.append([InlineKeyboardButton("👁️  Preview Post", callback_data="preview")])
        keyboard.append([InlineKeyboardButton("📤  Post to Channel", callback_data="post")])

    return InlineKeyboardMarkup(keyboard)

def main_menu_text(draft: dict) -> str:
    btns = draft["buttons"]
    lines = ["<b>📋 Channel Post Builder</b>\n"]
    lines.append(f"<b>Message:</b>\n<i>{draft['text'][:200]}</i>\n")
    if btns:
        lines.append("<b>Buttons:</b>")
        for i, b in enumerate(btns, 1):
            lines.append(f"  {i}. {style_emoji(b.get('style',''))} <b>{b['label']}</b>  →  {b['url']}  [row {b.get('row',0)+1}]")
    else:
        lines.append("<i>No buttons yet — add one below.</i>")
    return "\n".join(lines)

# ─── Handlers ──────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_session(context)
    await update.message.reply_text(
        main_menu_text(draft),
        parse_mode="HTML",
        reply_markup=build_main_menu(draft),
    )
    return MAIN_MENU


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    draft = get_session(context)
    data = query.data

    # ── Set post text ──
    if data == "set_text":
        await query.edit_message_text(
            "✏️ <b>Send your post text now.</b>\n\n"
            "You can use HTML tags: <code>&lt;b&gt;</code>, <code>&lt;i&gt;</code>, <code>&lt;a href='...'&gt;</code>\n\n"
            "Type /cancel to go back.",
            parse_mode="HTML",
        )
        return TYPING_POST_TEXT

    # ── Add button ──
    elif data == "add_button":
        context.user_data["new_btn"] = {}
        await query.edit_message_text(
            "🔤 <b>Enter the button label</b> (the text shown on the button):\n\nType /cancel to go back.",
            parse_mode="HTML",
        )
        return TYPING_BUTTON_LABEL

    # ── Remove last button ──
    elif data == "remove_last":
        if draft["buttons"]:
            removed = draft["buttons"].pop()
            notice = f"Removed button: <b>{removed['label']}</b>"
        else:
            notice = "No buttons to remove."
        await query.edit_message_text(
            f"{notice}\n\n{main_menu_text(draft)}",
            parse_mode="HTML",
            reply_markup=build_main_menu(draft),
        )
        return MAIN_MENU

    # ── Preview ──
    elif data == "preview":
        markup = build_preview_markup(draft)
        await query.message.reply_text(
            "👁️ <b>Preview — this is exactly what will be posted:</b>",
            parse_mode="HTML",
        )
        await query.message.reply_text(
            draft["text"],
            parse_mode="HTML",
            reply_markup=markup,
        )
        # Show menu again
        await query.message.reply_text(
            main_menu_text(draft),
            parse_mode="HTML",
            reply_markup=build_main_menu(draft),
        )
        return MAIN_MENU

    # ── Post to channel ──
    elif data == "post":
        markup = build_preview_markup(draft)
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=draft["text"],
                parse_mode="HTML",
                reply_markup=markup,
            )
            await query.edit_message_text(
                "✅ <b>Posted to channel successfully!</b>\n\nSend /start to create a new post.",
                parse_mode="HTML",
            )
            context.user_data.clear()
        except Exception as e:
            await query.edit_message_text(
                f"❌ <b>Failed to post:</b> <code>{e}</code>\n\n"
                "Make sure the bot is an admin in your channel.\n\nSend /start to try again.",
                parse_mode="HTML",
            )
        return ConversationHandler.END

    return MAIN_MENU


async def receive_post_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_session(context)
    draft["text"] = update.message.text
    await update.message.reply_text(
        f"✅ Post text saved!\n\n{main_menu_text(draft)}",
        parse_mode="HTML",
        reply_markup=build_main_menu(draft),
    )
    return MAIN_MENU


async def receive_button_label(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_btn"]["label"] = update.message.text
    await update.message.reply_text(
        "🔗 <b>Now send the URL</b> for this button (must start with https://):",
        parse_mode="HTML",
    )
    return TYPING_BUTTON_URL


async def receive_button_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("⚠️ URL must start with <code>https://</code> — try again:", parse_mode="HTML")
        return TYPING_BUTTON_URL

    context.user_data["new_btn"]["url"] = url

    # Ask for color
    keyboard = [
        [
            InlineKeyboardButton("🔵 Primary (Blue)", callback_data="color_primary"),
            InlineKeyboardButton("🟢 Success (Green)", callback_data="color_success"),
        ],
        [
            InlineKeyboardButton("🔴 Danger (Red)", callback_data="color_danger"),
            InlineKeyboardButton("⚪ Default (Gray)", callback_data="color_default"),
        ],
    ]
    await update.message.reply_text(
        "🎨 <b>Choose button color:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_BUTTON_COLOR


async def choose_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    color_map = {
        "color_primary": "primary",
        "color_success": "success",
        "color_danger": "danger",
        "color_default": "",
    }
    context.user_data["new_btn"]["style"] = color_map.get(query.data, "")

    # Ask which row
    draft = get_session(context)
    existing_rows = sorted(set(b.get("row", 0) for b in draft["buttons"]))
    keyboard = []

    # Existing rows
    if existing_rows:
        row_btns = [InlineKeyboardButton(f"Row {r+1}", callback_data=f"row_{r}") for r in existing_rows]
        keyboard.append(row_btns)

    # New row option
    next_row = (max(existing_rows) + 1) if existing_rows else 0
    keyboard.append([InlineKeyboardButton(f"➕ New Row (Row {next_row+1})", callback_data=f"row_{next_row}")])

    await query.edit_message_text(
        "📐 <b>Which row should this button go in?</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CHOOSING_BUTTON_ROW


async def choose_row(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    row = int(query.data.split("_")[1])
    context.user_data["new_btn"]["row"] = row

    # Save button
    draft = get_session(context)
    draft["buttons"].append(dict(context.user_data["new_btn"]))
    context.user_data.pop("new_btn", None)

    btn = draft["buttons"][-1]
    await query.edit_message_text(
        f"✅ Button added: {style_emoji(btn['style'])} <b>{btn['label']}</b>\n\n"
        + main_menu_text(draft),
        parse_mode="HTML",
        reply_markup=build_main_menu(draft),
    )
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = get_session(context)
    await update.message.reply_text(
        main_menu_text(draft),
        parse_mode="HTML",
        reply_markup=build_main_menu(draft),
    )
    return MAIN_MENU


# ─── App ───────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(main_menu_callback),
            ],
            TYPING_POST_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_post_text),
                CommandHandler("cancel", cancel),
            ],
            TYPING_BUTTON_LABEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_button_label),
                CommandHandler("cancel", cancel),
            ],
            TYPING_BUTTON_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_button_url),
                CommandHandler("cancel", cancel),
            ],
            CHOOSING_BUTTON_COLOR: [
                CallbackQueryHandler(choose_color, pattern="^color_"),
            ],
            CHOOSING_BUTTON_ROW: [
                CallbackQueryHandler(choose_row, pattern="^row_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )

    app.add_handler(conv)
    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
