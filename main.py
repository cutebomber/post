import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = "8641638446:AAHU1q4tSijiW1alAZSUhUcf9oucPPi1SlM"       # from @BotFather
CHANNEL_ID = "@chillflames"  # or numeric ID like -1001234567890

async def post_to_channel():
    bot = Bot(token=BOT_TOKEN)

    # Build colored inline buttons
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Join Now",
                url="https://t.me/your_link",
                style="success"      # GREEN
            ),
            InlineKeyboardButton(
                text="🔗 Website",
                url="https://yourwebsite.com",
                style="primary"      # BLUE
            ),
        ],
        [
            InlineKeyboardButton(
                text="❌ Unsubscribe",
                callback_data="unsub",
                style="danger"       # RED
            ),
        ],
        [
            InlineKeyboardButton(
                text="More Info",    # no style = default gray
                callback_data="info"
            ),
        ]
    ]

    markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(
        chat_id=CHANNEL_ID,
        text="👋 *Welcome to our channel!*\n\nChoose an option below:",
        parse_mode="Markdown",
        reply_markup=markup
    )
    print("Posted successfully!")

asyncio.run(post_to_channel())
