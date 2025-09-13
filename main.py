"""
Automated News Bot - Main Application
=====================================
Orchestrates all components for comprehensive news automation
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Add core directory to path
sys.path.append('.')

from core.config_manager import ConfigManager
from core.websub_subscriber import create_websub_subscriber
from core.ai_processor import create_ai_processor
from core.deduplication_engine import create_deduplication_engine
from social.twitter_bot import create_twitter_bot
from social.facebook_poster import create_facebook_poster
from social.telegram_poster import create_telegram_poster

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('news_bot.log')
    ]
)

logger = logging.getLogger(__name__)


class NewsAutomationBot:
    """Main orchestrator for the news automation system"""
    
    def __init__(self):
        self.config_manager = None
        self.websub_subscriber = None
        self.ai_processor = None
        self.dedup_engine = None
        self.twitter_bot = None
        self.facebook_poster = None
        self.telegram_poster = None
        
        # System state
        self.running = False
        self.emergency_stop = False
        
        # Statistics
        self.stats = {
            'items_processed': 0,
            'items_posted': 0,
            'duplicates_filtered': 0,
            'errors': 0,
            'start_time': None
        }
    
    async def initialize(self) -> bool:
        """Initialize all components"""
        try:
            logger.info("Initializing News Automation Bot...")
            
            # Load configuration
            self.config_manager = ConfigManager()
            logger.info("Configuration loaded")
            
            # Initialize AI processor
            self.ai_processor = create_ai_processor(self.config_manager)
            if not self.ai_processor:
                raise Exception("Failed to create AI processor")
            logger.info("AI processor initialized")
            
            # Initialize deduplication engine
            self.dedup_engine = create_deduplication_engine(self.config_manager)
            if not self.dedup_engine:
                raise Exception("Failed to create deduplication engine")
            logger.info("Deduplication engine initialized")
            
            # Initialize WebSub subscriber
            self.websub_subscriber = create_websub_subscriber(self.config_manager)
            if not self.websub_subscriber:
                raise Exception("Failed to create WebSub subscriber")
            self.websub_subscriber.add_callback_handler(self.process_news_item)
            logger.info("WebSub subscriber initialized")
            
            # Initialize social media posters
            self.facebook_poster = create_facebook_poster(self.config_manager)
            self.telegram_poster = create_telegram_poster(self.config_manager)
            if not self.facebook_poster or not self.telegram_poster:
                raise Exception("Failed to create social media posters")
            logger.info("Social media posters initialized")
            
            # Initialize Twitter bot (requires special handling)
            self.twitter_bot = create_twitter_bot(self.config_manager, self.ai_processor)
            if not self.twitter_bot:
                raise Exception("Failed to create Twitter bot")
            logger.info("Twitter bot created (will initialize when needed)")
            
            # Subscribe to news feeds
            await self.websub_subscriber.subscribe_to_feeds()
            logger.info("Subscribed to news feeds")
            
            self.stats['start_time'] = datetime.now()
            logger.info("News Automation Bot initialized successfully!")
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return False
    
    async def process_news_item(self, news_item: Dict[str, Any]) -> None:
        """Process incoming news item"""
        try:
            if self.emergency_stop:
                logger.warning("Emergency stop active - skipping news item")
                return
            
            logger.info(f"Processing news: {news_item.get('title', '')[:50]}...")
            self.stats['items_processed'] += 1
            
            # Check for duplicates
            is_duplicate, reason, similarity = await self.dedup_engine.is_duplicate(
                news_item.get('content', ''),
                news_item.get('title', ''),
                news_item.get('link', '')
            )
            
            if is_duplicate:
                logger.debug(f"Duplicate filtered: {reason} (similarity: {similarity:.2f})")
                self.stats['duplicates_filtered'] += 1
                return
            
            # Analyze content quality
            content_analysis = await self.ai_processor.analyze_content_quality(
                news_item.get('content', '') or news_item.get('summary', '')
            )
            
            # Skip low-quality content
            quality_threshold = self.config_manager.get_content_config().get('quality_threshold', 0.7)
            if content_analysis.get('quality_score', 0) < quality_threshold:
                logger.debug(f"Low quality content filtered: {content_analysis.get('quality_score', 0)}")
                return
            
            # Skip negative sentiment content (optional)
            if content_analysis.get('sentiment') == 'negative':
                logger.debug("Negative sentiment content filtered")
                return
            
            # Enhance content with AI
            enhanced_content = await self.ai_processor.enhance_content(
                news_item.get('content', '') or news_item.get('summary', ''),
                news_item.get('source', '')
            )
            
            if enhanced_content:
                news_item['enhanced_content'] = enhanced_content
            
            # Post to all platforms
            await self.post_to_platforms(news_item)
            
        except Exception as e:
            logger.error(f"News processing error: {e}")
            self.stats['errors'] += 1
    
    async def post_to_platforms(self, news_item: Dict[str, Any]) -> None:
        """Post news item to all configured platforms"""
        try:
            title = news_item.get('title', '')
            content = news_item.get('enhanced_content') or news_item.get('content', '') or news_item.get('summary', '')
            link = news_item.get('link', '')
            image_url = news_item.get('image_url')
            
            # Download image if available
            image_path = None
            if image_url:
                image_path = await self.download_image(image_url, news_item.get('id', 'unknown'))
            
            # Prepare content for social media
            social_content = f"{title}\n\n{content[:200]}...\n\n{link}"
            
            # Track posting success
            posted_successfully = False
            
            # Post to Twitter
            if self.config_manager.can_post_to_platform('twitter'):
                try:
                    # Generate Twitter-specific content
                    twitter_content = await self.ai_processor.generate_social_post(
                        social_content, 'twitter', news_item.get('source', '')
                    )
                    
                    if twitter_content:
                        # Check if content needs threading
                        char_limit = self.config_manager.get_twitter_config().get('limits', {}).get('character_limit', 280)
                        
                        if len(twitter_content) > char_limit and self.config_manager.get_twitter_config().get('limits', {}).get('thread_enabled', True):
                            # Create thread
                            thread_content = await self.ai_processor.create_thread_content(twitter_content, 'twitter')
                            if await self.ensure_twitter_ready() and await self.twitter_bot.post_thread(thread_content, [image_path] if image_path else None):
                                posted_successfully = True
                                logger.info("Posted Twitter thread")
                        else:
                            # Single tweet
                            if await self.ensure_twitter_ready() and await self.twitter_bot.post_tweet(twitter_content, image_path):
                                posted_successfully = True
                                logger.info("Posted to Twitter")
                
                except Exception as e:
                    logger.error(f"Twitter posting error: {e}")
            
            # Post to Facebook
            if self.config_manager.can_post_to_platform('facebook'):
                try:
                    if await self.facebook_poster.post_content(social_content, image_path):
                        posted_successfully = True
                        logger.info("Posted to Facebook")
                        
                except Exception as e:
                    logger.error(f"Facebook posting error: {e}")
            
            # Post to Telegram
            if self.config_manager.can_post_to_platform('telegram'):
                try:
                    if await self.telegram_poster.post_content(social_content, image_path):
                        posted_successfully = True
                        logger.info("Posted to Telegram")
                        
                except Exception as e:
                    logger.error(f"Telegram posting error: {e}")
            
            if posted_successfully:
                self.stats['items_posted'] += 1
                logger.info("News item posted successfully to platforms")
            
            # Clean up downloaded image
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Platform posting error: {e}")
            self.stats['errors'] += 1
    
    async def ensure_twitter_ready(self) -> bool:
        """Ensure Twitter bot is ready for posting"""
        try:
            if not self.twitter_bot.logged_in:
                return await self.twitter_bot.initialize()
            return True
        except Exception as e:
            logger.error(f"Twitter initialization error: {e}")
            return False
    
    async def download_image(self, image_url: str, item_id: str) -> Optional[str]:
        """Download image for posting"""
        try:
            import aiohttp
            import aiofiles
            
            # Create temp directory
            os.makedirs('temp_images', exist_ok=True)
            
            # Generate filename
            extension = image_url.split('.')[-1].split('?')[0] or 'jpg'
            filename = f"temp_images/{item_id}.{extension}"
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(filename, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                await f.write(chunk)
                        
                        logger.debug(f"Image downloaded: {filename}")
                        return filename
            
            return None
            
        except Exception as e:
            logger.error(f"Image download error: {e}")
            return None
    
    async def run_engagement_cycle(self) -> None:
        """Run Twitter engagement cycle"""
        try:
            if self.config_manager.is_emergency_stopped():
                return
            
            logger.info("Starting engagement cycle...")
            
            if await self.ensure_twitter_ready():
                await self.twitter_bot.engage_with_content()
                logger.info("Engagement cycle completed")
            
        except Exception as e:
            logger.error(f"Engagement cycle error: {e}")
    
    async def run_maintenance_tasks(self) -> None:
        """Run periodic maintenance tasks"""
        try:
            logger.info("Running maintenance tasks...")
            
            # Refresh WebSub subscriptions
            await self.websub_subscriber.refresh_subscriptions()
            
            # Clear caches if needed
            if self.stats['items_processed'] % 1000 == 0:
                self.ai_processor.clear_cache()
                await self.dedup_engine.clear_cache()
                logger.info("Caches cleared")
            
            # Check for daily limit reset
            current_time = datetime.now()
            if current_time.hour == 0 and current_time.minute < 5:  # Around midnight
                self.config_manager.reset_daily_limits()
                logger.info("Daily limits reset")
            
            logger.info("Maintenance tasks completed")
            
        except Exception as e:
            logger.error(f"Maintenance task error: {e}")
    
    async def run(self) -> None:
        """Run the main application loop"""
        try:
            logger.info("Starting News Automation Bot...")
            self.running = True
            
            # Start WebSub server in background
            websub_task = asyncio.create_task(self.websub_subscriber.start_server())
            
            # Start fallback polling in background - this is critical for bulletproof operation
            polling_task = asyncio.create_task(self.websub_subscriber.fallback_feed_polling())
            
            # Start RSS polling immediately (don't wait for WebSub failures)
            initial_poll_task = asyncio.create_task(self._run_initial_rss_poll())
            
            # Main loop for engagement and maintenance
            while self.running and not self.emergency_stop:
                try:
                    # Run engagement cycle every 5 minutes
                    await self.run_engagement_cycle()
                    await asyncio.sleep(300)  # 5 minutes
                    
                    # Run maintenance every hour
                    if self.stats['items_processed'] % 12 == 0:  # Approximate hourly
                        await self.run_maintenance_tasks()
                
                except KeyboardInterrupt:
                    logger.info("Received shutdown signal")
                    break
                except Exception as e:
                    logger.error(f"Main loop error: {e}")
                    await asyncio.sleep(60)  # Wait before retrying
            
            # Cleanup
            websub_task.cancel()
            polling_task.cancel()
            initial_poll_task.cancel()
            
            if self.twitter_bot:
                await self.twitter_bot.cleanup()
            
            logger.info("News Automation Bot stopped")
            
        except Exception as e:
            logger.error(f"Application run error: {e}")
            self.emergency_stop = True
    
    async def _run_initial_rss_poll(self) -> None:
        """Run initial RSS poll to ensure system works immediately"""
        try:
            logger.info("Running initial RSS poll to ensure bulletproof operation...")
            await asyncio.sleep(5)  # Wait for initialization
            
            # Force RSS polling since WebSub likely failed
            if hasattr(self.websub_subscriber, '_poll_all_configured_feeds'):
                await self.websub_subscriber._poll_all_configured_feeds()
                logger.info("Initial RSS poll completed - system is bulletproof!")
            else:
                logger.warning("RSS fallback method not available")
                
        except Exception as e:
            logger.error(f"Initial RSS poll error: {e}")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        uptime = (datetime.now() - self.stats['start_time']).seconds if self.stats['start_time'] else 0
        
        return {
            'uptime_seconds': uptime,
            'processing_stats': self.stats.copy(),
            'websub_stats': self.websub_subscriber.get_subscription_status() if self.websub_subscriber else {},
            'ai_stats': self.ai_processor.get_ai_status() if self.ai_processor else {},
            'dedup_stats': self.dedup_engine.get_stats() if self.dedup_engine else {},
            'twitter_stats': self.twitter_bot.get_stats() if self.twitter_bot else {},
            'config_status': {
                'emergency_stop': self.config_manager.is_emergency_stopped() if self.config_manager else False,
                'platform_limits': {
                    platform: {
                        'can_post': self.config_manager.can_post_to_platform(platform) if self.config_manager else False
                    }
                    for platform in ['twitter', 'facebook', 'telegram']
                }
            }
        }


async def main():
    """Main application entry point"""
    try:
        # Create and initialize bot
        bot = NewsAutomationBot()
        
        if not await bot.initialize():
            logger.error("Failed to initialize bot")
            return 1
        
        # Run the bot
        await bot.run()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\\nApplication interrupted")
        sys.exit(0)