from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

API_ID = 21752358        # from my.telegram.org
API_HASH = "fb46a136fed4a4de27ab057c7027fec3"
BOT_TOKEN = "8641638446:AAHU1q4tSijiW1alAZSUhUcf9oucPPi1SlM"

CHANNEL_ID = "@yourchannelusername"  # or -100xxxx id

app = Client("button-bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


@app.on_message()
async def send_post(client, message):
    # Only allow you (optional safety)
    if message.from_user.id != 123456789:
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🟢 Buy Now", url="https://t.me/yourlink"),
            InlineKeyboardButton("🔴 Cancel", callback_data="cancel")
        ],
        [
            InlineKeyboardButton("📩 Contact", url="https://t.me/yourusername")
        ]
    ])

    await client.send_message(
        chat_id=CHANNEL_ID,
        text=message.text,
        reply_markup=keyboard
    )


app.run()
