"""
Telegram Bot Integration
========================
Posts content to Telegram channels using Bot API
"""

import logging
from typing import Dict, List, Optional, Any
import aiofiles
import os

from telegram import Bot
from telegram.error import TelegramError

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class TelegramPoster:
    """Telegram channel posting automation"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.tg_config = config_manager.get_telegram_config()
        
        self.bot_token = self.tg_config.get('bot_token', '')
        self.channel_id = self.tg_config.get('channel_id', '')
        
        # Initialize bot
        self.bot = None
        if self.bot_token:
            try:
                self.bot = Bot(token=self.bot_token)
            except Exception as e:
                logger.error(f"Telegram bot initialization error: {e}")
    
    async def post_content(self, content: str, image_path: Optional[str] = None) -> bool:
        """Post content to Telegram channel"""
        try:
            if not self.bot or not self.channel_id:
                logger.error("Telegram bot not configured")
                return False
            
            # Check daily limits
            if not self.config.can_post_to_platform('telegram'):
                logger.warning("Daily post limit reached for Telegram")
                return False
            
            logger.info(f"Posting to Telegram: {content[:50]}...")
            
            # Post with or without image
            if image_path and os.path.exists(image_path):
                return await self._post_with_image(content, image_path)
            else:
                return await self._post_text_only(content)
                
        except Exception as e:
            logger.error(f"Telegram posting error: {e}")
            return False
    
    async def _post_text_only(self, content: str) -> bool:
        """Post text-only content"""
        try:
            message = await self.bot.send_message(
                chat_id=self.channel_id,
                text=content,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
            
            if message:
                self.config.record_platform_action('telegram', 'post')
                logger.info(f"Telegram message sent: {message.message_id}")
                return True
            
            return False
            
        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Telegram text post error: {e}")
            return False
    
    async def _post_with_image(self, content: str, image_path: str) -> bool:
        """Post content with image"""
        try:
            async with aiofiles.open(image_path, 'rb') as photo_file:
                message = await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=photo_file,
                    caption=content,
                    parse_mode='HTML'
                )
            
            if message:
                self.config.record_platform_action('telegram', 'post')
                logger.info(f"Telegram photo message sent: {message.message_id}")
                return True
            
            return False
            
        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Telegram image post error: {e}")
            return False


def create_telegram_poster(config_manager: ConfigManager) -> TelegramPoster:
    """Create and configure Telegram poster"""
    return TelegramPoster(config_manager)