import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import aiohttp

class TelegramNotifier:
    """Telegram bot for sending notifications and receiving feedback"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Telegram configuration
        self.enabled = config.get('telegram.enabled', False)
        self.bot_token = config.get('telegram.bot_token', '')
        self.chat_id = config.get('telegram.chat_id', '')
        self.proxy_enabled = config.get('telegram.proxy.enabled', False)
        self.proxy_url = config.get('telegram.proxy.url', '')
        
        # Initialize bot
        self.bot = None
        self.application = None
        
        if self.enabled and self.bot_token:
            self._initialize_bot()
    
    def _initialize_bot(self):
        """Initialize Telegram bot"""
        try:
            self.bot = Bot(token=self.bot_token)
            
            # Setup proxy if configured
            if self.proxy_enabled and self.proxy_url:
                import telegram.request
                request = telegram.request.BaseRequest(
                    connect_timeout=20,
                    read_timeout=20,
                    proxy_url=self.proxy_url
                )
                self.bot.request = request
            
            self.logger.info("Telegram bot initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing Telegram bot: {e}")
            self.enabled = False
    
    async def start_bot(self):
        """Start Telegram bot for receiving feedback"""
        if not self.enabled:
            return
        
        try:
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(CommandHandler("stats", self._handle_stats))
            self.application.add_handler(CommandHandler("help", self._handle_help))
            self.application.add_handler(CallbackQueryHandler(self._handle_callback))
            
            # Start bot
            await self.application.initialize()
            await self.application.start()
            
            self.logger.info("Telegram bot started for receiving feedback")
            
        except Exception as e:
            self.logger.error(f"Error starting Telegram bot: {e}")
    
    async def stop_bot(self):
        """Stop Telegram bot"""
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
            self.logger.info("Telegram bot stopped")
    
    async def send_notification(self, article: Dict[str, Any], summary_image_path: Optional[str] = None):
        """Send notification about interesting article"""
        if not self.enabled or not self.bot:
            return False
        
        try:
            # Create message
            message = self._create_message(article)
            
            # Create inline keyboard for feedback
            keyboard = self._create_feedback_keyboard(article)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send message with image if available
            if summary_image_path and Path(summary_image_path).exists():
                with open(summary_image_path, 'rb') as photo:
                    await self.bot.send_photo(
                        chat_id=self.chat_id,
                        photo=photo,
                        caption=message,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            
            self.logger.info(f"Sent notification for article: {article.get('title', '')[:50]}...")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False
    
    def _create_message(self, article: Dict[str, Any]) -> str:
        """Create notification message"""
        title = article.get('title', 'No Title')
        content = article.get('cleaned_content', '')
        link = article.get('link', '')
        source = article.get('source_url', '')
        
        # Truncate content for message
        if len(content) > 300:
            content = content[:300] + "..."
        
        # Extract domain from source
        if source:
            from urllib.parse import urlparse
            domain = urlparse(source).netloc
        else:
            domain = 'Unknown'
        
        message = f"""
🔍 <b>{title}</b>

📄 {content}

🌐 Source: {domain}
🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}
        """
        
        # Add link if available
        if link:
            message += f"\n🔗 <a href='{link}'>Read more</a>"
        
        return message
    
    def _create_feedback_keyboard(self, article: Dict[str, Any]) -> list:
        """Create inline keyboard for user feedback"""
        # Use article hash as callback data
        import hashlib
        article_hash = hashlib.md5(
            f"{article.get('title', '')}{article.get('scraped_at', '')}".encode()
        ).hexdigest()[:8]
        
        keyboard = [
            [
                InlineKeyboardButton("👍 Interested", callback_data=f"interested_{article_hash}"),
                InlineKeyboardButton("👎 Not Interested", callback_data=f"not_interested_{article_hash}")
            ],
            [
                InlineKeyboardButton("🔗 Open Link", callback_data=f"open_link_{article_hash}"),
                InlineKeyboardButton("📊 Stats", callback_data="stats")
            ]
        ]
        
        return keyboard
    
    async def _handle_start(self, update, context):
        """Handle /start command"""
        await update.message.reply_text(
            "🤖 Web Scanner Bot\n\n"
            "I'll send you notifications about interesting articles I find.\n"
            "You can provide feedback to help me learn your preferences.\n\n"
            "Commands:\n"
            "/stats - View scanning statistics\n"
            "/help - Show this help message"
        )
    
    async def _handle_stats(self, update, context):
        """Handle /stats command"""
        try:
            # Get statistics from learning database
            from .learning_database import LearningDatabase
            db = LearningDatabase(self.config)
            stats = db.get_statistics()
            
            message = f"""
📊 <b>Scanning Statistics</b>

📰 Total Articles: {stats.get('total_articles', 0)}
🎯 Articles with Feedback: {stats.get('articles_with_feedback', 0)}
💡 User Interest Rate: {stats.get('user_interest_rate', 0):.1%}
🕒 Last 24h: {stats.get('articles_last_24h', 0)} articles

🤖 Bot Status: {'✅ Active' if self.enabled else '❌ Inactive'}
        """
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            self.logger.error(f"Error handling stats command: {e}")
            await update.message.reply_text("❌ Error retrieving statistics")
    
    async def _handle_help(self, update, context):
        """Handle /help command"""
        help_text = """
🤖 <b>Web Scanner Bot Help</b>

I scan websites periodically and send you notifications about interesting articles.

<b>Features:</b>
• 🔍 Automatic website scanning
• 🛡️ TOR/VPN support for privacy
• 🧠 Learning algorithm for your preferences
• 🖼️ Summary image generation
• 📱 Telegram notifications

<b>Feedback Buttons:</b>
👍 Interested - I'll send you similar content
👎 Not Interested - I'll avoid similar content
🔗 Open Link - Open the article in your browser

<b>Commands:</b>
/start - Start the bot
/stats - View scanning statistics
/help - Show this help

<b>Configuration:</b>
Edit the config file to add websites and adjust filtering parameters.
        """
        
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    async def _handle_callback(self, update, context):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        try:
            callback_data = query.data
            parts = callback_data.split('_', 2)
            
            if len(parts) < 2:
                return
            
            action = parts[0]
            data = parts[1]
            
            if action == 'interested':
                await self._process_feedback(query, 'interested', data)
            elif action == 'not_interested':
                await self._process_feedback(query, 'not_interested', data)
            elif action == 'open_link':
                await self._open_article_link(query, data)
            elif action == 'stats':
                await self._handle_stats(query, context)
            
        except Exception as e:
            self.logger.error(f"Error handling callback: {e}")
            await query.edit_message_text("❌ Error processing your feedback")
    
    async def _process_feedback(self, query, feedback_type: str, article_hash: str):
        """Process user feedback"""
        try:
            # In a real implementation, you'd find the article by hash
            # For now, we'll just acknowledge the feedback
            
            feedback_messages = {
                'interested': "👍 Thanks! I'll send you more similar content.",
                'not_interested': "👎 Got it! I'll avoid similar content in the future."
            }
            
            await query.edit_message_text(feedback_messages.get(feedback_type, "✅ Feedback received"))
            
            # Here you would typically:
            # 1. Find the article in the database
            # 2. Record the feedback
            # 3. Retrain the learning model
            
            self.logger.info(f"Received feedback: {feedback_type} for article {article_hash}")
            
        except Exception as e:
            self.logger.error(f"Error processing feedback: {e}")
    
    async def _open_article_link(self, query, article_hash: str):
        """Open article link (would typically find and send the actual link)"""
        try:
            # In a real implementation, you'd find the article by hash
            # and send the actual link
            
            await query.edit_message_text("🔗 Opening article link...")
            
            # Here you would typically find the article and send the link
            
        except Exception as e:
            self.logger.error(f"Error opening article link: {e}")
    
    async def send_test_message(self):
        """Send test message to verify bot is working"""
        if not self.enabled or not self.bot:
            return False
        
        try:
            message = f"""
🧪 <b>Test Message</b>

Web Scanner Bot is working correctly!

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: ✅ Active
            """
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            
            self.logger.info("Test message sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending test message: {e}")
            return False
    
    async def send_error_notification(self, error_message: str):
        """Send error notification to admin"""
        if not self.enabled or not self.bot:
            return
        
        try:
            message = f"""
🚨 <b>Scanner Error</b>

{error_message}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            
        except Exception as e:
            self.logger.error(f"Error sending error notification: {e}")
    
    def is_enabled(self) -> bool:
        """Check if Telegram notifications are enabled"""
        return self.enabled and bool(self.bot_token) and bool(self.chat_id)