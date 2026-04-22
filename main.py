import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from telegram import (
    Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup,
    Message, ChatMember, Chat, MessageEntity
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
POST_TITLE, POST_CONTENT, POST_BUTTONS, BUTTON_EDIT, PREVIEW_POST = range(5)

# Store temporary post data for each user
user_post_data: Dict[int, Dict] = {}

class TelegramPostBot:
    def __init__(self, token: str, channel_username: str, admin_user_ids: List[int]):
        """
        Initialize the bot
        
        Args:
            token: Telegram bot token
            channel_username: Channel username (without @)
            admin_user_ids: List of Telegram user IDs who are admins
        """
        self.token = token
        self.channel_username = channel_username
        self.admin_user_ids = admin_user_ids
        self.application = None
        
    async def check_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if user is admin of the bot"""
        user_id = update.effective_user.id
        if user_id not in self.admin_user_ids:
            await update.message.reply_text(
                "❌ You are not authorized to use this bot.",
                parse_mode=ParseMode.HTML
            )
            return False
        return True
    
    async def check_channel_admin(self, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Check if bot is admin in the channel"""
        try:
            chat_member = await context.bot.get_chat_member(
                chat_id=f"@{self.channel_username}",
                user_id=context.bot.id
            )
            return chat_member.status in ['administrator', 'creator']
        except Exception as e:
            logger.error(f"Bot is not admin in channel: {e}")
            return False
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        if not await self.check_admin(update, context):
            return
        
        await update.message.reply_text(
            "🎨 <b>Welcome to Advanced Post Creator Bot!</b>\n\n"
            "I can help you create beautiful posts with colored inline buttons\n"
            "and premium custom emojis for your channel.\n\n"
            "<b>Commands:</b>\n"
            "/newpost - Create a new post\n"
            "/cancel - Cancel current operation\n"
            "/help - Show this help message\n\n"
            "<b>Features:</b>\n"
            "• Colored inline buttons\n"
            "• Premium custom emojis\n"
            "• Rich text formatting\n"
            "• Post preview before sending",
            parse_mode=ParseMode.HTML
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command handler"""
        if not await self.check_admin(update, context):
            return
        
        await update.message.reply_text(
            "📖 <b>How to create a post:</b>\n\n"
            "1️⃣ Use /newpost to start\n"
            "2️⃣ Enter post title (with emojis if desired)\n"
            "3️⃣ Enter post content with formatting\n"
            "4️⃣ Add buttons (or skip)\n"
            "5️⃣ Preview and send to channel\n\n"
            "<b>Button Format:</b>\n"
            "Use: <code>button_text|url|color</code>\n"
            "Example: <code>Visit Website|https://example.com|blue</code>\n\n"
            "<b>Available Colors:</b>\n"
            "🔵 blue, 🟢 green, 🔴 red, 🟡 yellow, 🟣 purple\n\n"
            "<b>Premium Emojis:</b>\n"
            "Just paste premium emojis directly into text!\n\n"
            "<b>Formatting:</b>\n"
            "Use HTML: &lt;b&gt;bold&lt;/b&gt;, &lt;i&gt;italic&lt;/i&gt;, &lt;a href='url'&gt;link&lt;/a&gt;",
            parse_mode=ParseMode.HTML
        )
    
    async def new_post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start new post creation"""
        if not await self.check_admin(update, context):
            return
        
        user_id = update.effective_user.id
        user_post_data[user_id] = {
            'title': None,
            'content': None,
            'buttons': []
        }
        
        await update.message.reply_text(
            "📝 <b>Create New Post</b>\n\n"
            "Please send me the <b>post title</b>.\n"
            "You can use:\n"
            "• Regular emojis 🎉\n"
            "• Premium custom emojis (if you have Telegram Premium)\n"
            "• HTML formatting\n\n"
            "Send /cancel to stop.",
            parse_mode=ParseMode.HTML
        )
        
        return POST_TITLE
    
    async def get_post_title(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle post title input"""
        user_id = update.effective_user.id
        title = update.message.text
        
        if title == '/cancel':
            await self.cancel(update, context)
            return ConversationHandler.END
        
        user_post_data[user_id]['title'] = title
        
        await update.message.reply_text(
            "✍️ <b>Great! Now send me the post content.</b>\n\n"
            "<b>Supported formatting:</b>\n"
            "• &lt;b&gt;bold&lt;/b&gt;\n"
            "• &lt;i&gt;italic&lt;/i&gt;\n"
            "• &lt;code&gt;code&lt;/code&gt;\n"
            "• &lt;a href='URL'&gt;link&lt;/a&gt;\n"
            "• Custom emojis (premium supported)\n\n"
            "Send your content:",
            parse_mode=ParseMode.HTML
        )
        
        return POST_CONTENT
    
    async def get_post_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle post content input"""
        user_id = update.effective_user.id
        content = update.message.text
        
        if content == '/cancel':
            await self.cancel(update, context)
            return ConversationHandler.END
        
        user_post_data[user_id]['content'] = content
        
        await update.message.reply_text(
            "🔘 <b>Now let's add buttons!</b>\n\n"
            "Send buttons in this format (one per line):\n"
            "<code>button_text|url|color</code>\n\n"
            "<b>Available colors:</b>\n"
            "blue, green, red, yellow, purple\n\n"
            "Examples:\n"
            "<code>Visit Site|https://example.com|blue</code>\n"
            "<code>Buy Now|https://store.com|green</code>\n"
            "<code>Learn More|https://docs.com|purple</code>\n\n"
            "Send <b>done</b> when finished, or <b>skip</b> for no buttons.",
            parse_mode=ParseMode.HTML
        )
        
        return POST_BUTTONS
    
    def get_color_code(self, color: str) -> str:
        """Convert color name to Telegram button color code"""
        colors = {
            'blue': 'primary',
            'green': 'success',
            'red': 'danger',
            'yellow': 'warning',
            'purple': 'secondary'
        }
        return colors.get(color.lower(), 'primary')
    
    async def add_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button addition"""
        user_id = update.effective_user.id
        text = update.message.text
        
        if text.lower() == 'done':
            return await self.show_preview(update, context)
        
        if text.lower() == 'skip':
            user_post_data[user_id]['buttons'] = []
            return await self.show_preview(update, context)
        
        # Parse button
        try:
            parts = text.split('|')
            if len(parts) != 3:
                await update.message.reply_text(
                    "❌ Invalid format! Use: <code>text|url|color</code>\n"
                    "Example: <code>Click Me|https://example.com|blue</code>",
                    parse_mode=ParseMode.HTML
                )
                return POST_BUTTONS
            
            button_text, url, color = parts
            color_code = self.get_color_code(color)
            
            user_post_data[user_id]['buttons'].append({
                'text': button_text.strip(),
                'url': url.strip(),
                'color': color_code
            })
            
            await update.message.reply_text(
                f"✅ Button added! Current buttons: {len(user_post_data[user_id]['buttons'])}\n"
                f"Send another button, 'done', or 'skip' to finish.",
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Error: {str(e)}\nPlease use correct format.",
                parse_mode=ParseMode.HTML
            )
        
        return POST_BUTTONS
    
    async def show_preview(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show post preview before sending"""
        user_id = update.effective_user.id
        post_data = user_post_data.get(user_id)
        
        if not post_data:
            await update.message.reply_text("❌ No post data found. Start with /newpost")
            return ConversationHandler.END
        
        # Build post content
        content = f"<b>{post_data['title']}</b>\n\n{post_data['content']}"
        
        # Create buttons
        keyboard = []
        for button in post_data['buttons']:
            keyboard.append([InlineKeyboardButton(
                text=button['text'],
                url=button['url']
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # Send preview
        preview_message = await update.message.reply_text(
            f"<b>📱 POST PREVIEW</b>\n\n{content}\n\n"
            f"<b>Buttons:</b> {len(post_data['buttons'])}\n"
            f"<b>Total characters:</b> {len(content)}\n\n"
            f"✅ Ready to send? Reply with 'send' to post to channel, "
            f"or 'edit' to modify, or 'cancel' to abort.",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        
        return PREVIEW_POST
    
    async def handle_preview_response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle preview response (send/edit/cancel)"""
        user_id = update.effective_user.id
        response = update.message.text.lower()
        
        if response == 'send':
            await self.send_to_channel(update, context)
            return ConversationHandler.END
        
        elif response == 'edit':
            await update.message.reply_text(
                "✏️ What would you like to edit?\n"
                "Send 'title', 'content', or 'buttons'",
                parse_mode=ParseMode.HTML
            )
            return BUTTON_EDIT
        
        elif response == 'cancel':
            await self.cancel(update, context)
            return ConversationHandler.END
        
        else:
            await update.message.reply_text(
                "Please reply with 'send', 'edit', or 'cancel'",
                parse_mode=ParseMode.HTML
            )
            return PREVIEW_POST
    
    async def edit_post_part(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle editing different parts of the post"""
        user_id = update.effective_user.id
        edit_part = update.message.text.lower()
        
        if edit_part == 'title':
            await update.message.reply_text("Send new title:")
            return POST_TITLE
        elif edit_part == 'content':
            await update.message.reply_text("Send new content:")
            return POST_CONTENT
        elif edit_part == 'buttons':
            user_post_data[user_id]['buttons'] = []
            await update.message.reply_text("Send new buttons (or 'skip'):")
            return POST_BUTTONS
        else:
            await update.message.reply_text("Invalid option. Send 'title', 'content', or 'buttons'")
            return BUTTON_EDIT
    
    async def send_to_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send the final post to channel"""
        user_id = update.effective_user.id
        post_data = user_post_data.get(user_id)
        
        if not post_data:
            await update.message.reply_text("❌ No post data found.")
            return
        
        # Check bot is admin in channel
        if not await self.check_channel_admin(context):
            await update.message.reply_text(
                f"❌ Bot is not an admin in @{self.channel_username}\n"
                f"Please add bot as admin first!",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Build final post
        content = f"<b>{post_data['title']}</b>\n\n{post_data['content']}"
        
        # Create buttons
        keyboard = []
        for button in post_data['buttons']:
            keyboard.append([InlineKeyboardButton(
                text=button['text'],
                url=button['url']
            )])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        try:
            # Send to channel
            sent_message = await context.bot.send_message(
                chat_id=f"@{self.channel_username}",
                text=content,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
            await update.message.reply_text(
                f"✅ <b>Post published successfully!</b>\n\n"
                f"📊 <b>Stats:</b>\n"
                f"• Title: {post_data['title'][:50]}...\n"
                f"• Buttons: {len(post_data['buttons'])}\n"
                f"• Message ID: {sent_message.message_id}\n\n"
                f"🔗 <a href='https://t.me/{self.channel_username}/{sent_message.message_id}'>View Post</a>",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            
            # Clear stored data
            del user_post_data[user_id]
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Failed to send post: {str(e)}\n\n"
                f"Make sure:\n"
                f"• Bot is admin in @{self.channel_username}\n"
                f"• Channel exists and is public\n"
                f"• Content doesn't violate Telegram rules",
                parse_mode=ParseMode.HTML
            )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current operation"""
        user_id = update.effective_user.id
        if user_id in user_post_data:
            del user_post_data[user_id]
        
        await update.message.reply_text(
            "❌ Operation cancelled.",
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ An error occurred. Please try again later.",
                parse_mode=ParseMode.HTML
            )
    
    def run(self):
        """Run the bot"""
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Create conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('newpost', self.new_post)],
            states={
                POST_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_post_title)],
                POST_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_post_content)],
                POST_BUTTONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_buttons)],
                BUTTON_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_post_part)],
                PREVIEW_POST: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_preview_response)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )
        
        # Add handlers
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('help', self.help_command))
        self.application.add_error_handler(self.error_handler)
        
        # Start bot
        print(f"🤖 Bot started! Add @{self.application.bot.username} as admin to @{self.channel_username}")
        print("Press Ctrl+C to stop...")
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

# Configuration
BOT_TOKEN = "8651990559:AAHk3DToBDJCgz57OJf88AtqcLLiS-S2myk"  # Replace with your bot token
CHANNEL_USERNAME = "@laveiuus"  # Replace with channel username (without @)
ADMIN_USER_IDS = [1899208318]  # Replace with your Telegram user IDs

if __name__ == "__main__":
    # Create and run bot
    bot = TelegramPostBot(
        token=BOT_TOKEN,
        channel_username=CHANNEL_USERNAME,
        admin_user_ids=ADMIN_USER_IDS
    )
    
    try:
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped!")
    except Exception as e:
        print(f"❌ Error: {e}")
