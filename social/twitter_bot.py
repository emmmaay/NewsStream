"""
Advanced Twitter Automation Bot with Human-like Behavior
========================================================
Ultra-realistic Twitter bot using Playwright for human-like engagement
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page, Browser
from fake_useragent import UserAgent

from core.config_manager import ConfigManager
from core.ai_processor import AIProcessor

logger = logging.getLogger(__name__)


class HumanBehaviorSimulator:
    """Simulates human-like behavior patterns for Twitter interaction"""
    
    def __init__(self, behavior_config: Dict[str, Any]):
        self.config = behavior_config
        self.user_agent = UserAgent()
        
    async def human_delay(self, action_type: str = "general") -> None:
        """Add human-like delay between actions"""
        delays = self.config.get('human_delays', {})
        
        if action_type == "typing":
            min_delay = delays.get('min_typing_delay', 0.1)
            max_delay = delays.get('max_typing_delay', 0.4)
        elif action_type == "scrolling":
            min_delay = delays.get('min_scroll_delay', 2.0)
            max_delay = delays.get('max_scroll_delay', 8.0)
        else:
            min_delay = delays.get('min_action_delay', 3.0)
            max_delay = delays.get('max_action_delay', 12.0)
        
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    async def human_scroll(self, page: Page) -> None:
        """Perform human-like scrolling"""
        try:
            scroll_config = self.config.get('scroll_patterns', {})
            if not scroll_config.get('enabled', True):
                return
            
            scroll_distance = scroll_config.get('scroll_distance', 500)
            pause_probability = scroll_config.get('pause_probability', 0.3)
            
            # Scroll down with variations
            for _ in range(random.randint(2, 5)):
                # Add some randomness to scroll distance
                distance = scroll_distance + random.randint(-100, 100)
                
                await page.evaluate(f"window.scrollBy(0, {distance})")
                
                # Random pause while scrolling
                if random.random() < pause_probability:
                    await self.human_delay("scrolling")
                else:
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                    
        except Exception as e:
            logger.error(f"Human scroll error: {e}")
    
    async def human_type(self, page: Page, selector: str, text: str) -> None:
        """Type text with human-like typing patterns"""
        try:
            element = await page.wait_for_selector(selector, timeout=10000)
            await element.click()
            
            # Clear existing text
            await element.fill("")
            
            # Type with human-like delays
            for char in text:
                await element.type(char)
                if char == ' ':
                    await self.human_delay("typing")
                else:
                    # Vary typing speed
                    await asyncio.sleep(random.uniform(0.05, 0.15))
            
            # Random pause after typing
            await self.human_delay("general")
            
        except Exception as e:
            logger.error(f"Human typing error: {e}")
            raise
    
    def get_random_user_agent(self) -> str:
        """Get random user agent string"""
        return self.user_agent.random


class TwitterBot:
    """Advanced Twitter automation bot with human-like behavior"""
    
    def __init__(self, config_manager: ConfigManager, ai_processor: AIProcessor):
        self.config = config_manager
        self.ai_processor = ai_processor
        
        # Twitter configuration
        self.twitter_config = config_manager.get_twitter_config()
        self.account_config = self.twitter_config.get('account', {})
        self.engagement_config = self.twitter_config.get('engagement', {})
        self.limits_config = self.twitter_config.get('limits', {})
        
        # Behavior simulator
        behavior_config = config_manager.get_human_behavior_config()
        self.behavior = HumanBehaviorSimulator(behavior_config)
        
        # Browser and page references
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        # State tracking
        self.logged_in = False
        self.last_refresh = None
        self.session_start = None
        
        # Engagement tracking
        self.daily_actions = {
            'posts': 0,
            'likes': 0,
            'retweets': 0,
            'replies': 0
        }
        
        # Cache for processed tweets
        self.processed_tweets = set()
        
    async def initialize(self) -> bool:
        """Initialize browser and login to Twitter"""
        try:
            logger.info("Initializing Twitter bot...")
            
            # Check if Twitter credentials are properly configured
            username = self.account_config.get('username', '')
            password = self.account_config.get('password', '')
            
            if not username or not password or 'YOUR_TWITTER' in username:
                logger.warning("Twitter credentials not configured - Twitter bot disabled")
                return False
            
            # Launch Playwright
            self.playwright = await async_playwright().start()
            
            # Launch browser with human-like settings (headless in production)
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Headless for server environments
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            
            # Create context with human-like settings
            context = await self.browser.new_context(
                user_agent=self.behavior.get_random_user_agent(),
                viewport={'width': 1366, 'height': 768}
            )
            
            # Add stealth settings
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # Create page
            self.page = await context.new_page()
            
            # Login to Twitter
            await self._login()
            
            self.session_start = datetime.now()
            logger.info("Twitter bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Twitter bot initialization error: {e}")
            await self.cleanup()
            return False
    
    async def _login(self) -> None:
        """Login to Twitter with human-like behavior"""
        try:
            logger.info("Logging in to Twitter...")
            
            # Navigate to Twitter login
            await self.page.goto("https://twitter.com/login", wait_until="networkidle")
            await self.behavior.human_delay()
            
            # Enter username
            username_selector = 'input[name="text"]'
            await self.behavior.human_type(self.page, username_selector, self.account_config.get('username', ''))
            
            # Click Next
            next_button = await self.page.wait_for_selector('div[role="button"]:has-text("Next")')
            await next_button.click()
            await self.behavior.human_delay()
            
            # Handle email verification if required
            try:
                email_input = await self.page.wait_for_selector('input[name="text"]', timeout=5000)
                if email_input:
                    await self.behavior.human_type(self.page, 'input[name="text"]', self.account_config.get('email', ''))
                    next_button = await self.page.wait_for_selector('div[role="button"]:has-text("Next")')
                    await next_button.click()
                    await self.behavior.human_delay()
            except:
                pass  # No email verification required
            
            # Enter password
            password_selector = 'input[name="password"]'
            await self.behavior.human_type(self.page, password_selector, self.account_config.get('password', ''))
            
            # Click Login
            login_button = await self.page.wait_for_selector('div[role="button"]:has-text("Log in")')
            await login_button.click()
            
            # Wait for login to complete
            await self.page.wait_for_url("https://twitter.com/home", timeout=30000)
            
            self.logged_in = True
            logger.info("Successfully logged in to Twitter")
            
        except Exception as e:
            logger.error(f"Twitter login error: {e}")
            raise
    
    async def post_tweet(self, content: str, image_path: Optional[str] = None, is_thread: bool = False) -> bool:
        """Post a tweet with human-like behavior"""
        try:
            if not self.logged_in:
                raise Exception("Not logged in to Twitter")
            
            # Check daily limits
            if not self.config.can_post_to_platform('twitter'):
                logger.warning("Daily post limit reached for Twitter")
                return False
            
            logger.info(f"Posting tweet: {content[:50]}...")
            
            # Navigate to home if not there
            await self._ensure_on_home()
            
            # Click compose tweet
            compose_selector = 'div[data-testid="tweetButtonInline"]'
            try:
                compose_button = await self.page.wait_for_selector(compose_selector, timeout=5000)
            except:
                # Alternative selector
                compose_button = await self.page.wait_for_selector('a[href="/compose/tweet"]')
            
            await compose_button.click()
            await self.behavior.human_delay()
            
            # Type tweet content
            tweet_input_selector = 'div[data-testid="tweetTextarea_0"]'
            await self.behavior.human_type(self.page, tweet_input_selector, content)
            
            # Add image if provided
            if image_path:
                await self._add_image_to_tweet(image_path)
            
            # Post the tweet
            tweet_button = await self.page.wait_for_selector('div[data-testid="tweetButtonInline"]')
            await tweet_button.click()
            
            # Wait for tweet to be posted
            await self.behavior.human_delay("general")
            
            # Record action
            self.config.record_platform_action('twitter', 'post')
            self.daily_actions['posts'] += 1
            
            logger.info("Tweet posted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Tweet posting error: {e}")
            return False
    
    async def post_thread(self, thread_content: List[str], images: Optional[List[str]] = None) -> bool:
        """Post a Twitter thread"""
        try:
            if not thread_content:
                return False
            
            logger.info(f"Posting thread with {len(thread_content)} tweets")
            
            # Post first tweet
            first_image = images[0] if images else None
            if not await self.post_tweet(f"{thread_content[0]} (1/{len(thread_content)})", first_image):
                return False
            
            # Add replies for remaining tweets
            for i, tweet_content in enumerate(thread_content[1:], 2):
                await self.behavior.human_delay("general")
                
                # Click reply to continue thread
                reply_button = await self.page.wait_for_selector('div[data-testid="reply"]')
                await reply_button.click()
                await self.behavior.human_delay()
                
                # Type reply content
                reply_content = f"{tweet_content} ({i}/{len(thread_content)})"
                tweet_input_selector = 'div[data-testid="tweetTextarea_0"]'
                await self.behavior.human_type(self.page, tweet_input_selector, reply_content)
                
                # Add image if available
                if images and i-1 < len(images):
                    await self._add_image_to_tweet(images[i-1])
                
                # Post reply
                reply_tweet_button = await self.page.wait_for_selector('div[data-testid="tweetButtonInline"]')
                await reply_tweet_button.click()
                
                await self.behavior.human_delay("general")
            
            logger.info("Thread posted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Thread posting error: {e}")
            return False
    
    async def engage_with_content(self) -> None:
        """Engage with content based on keywords and target users"""
        try:
            logger.info("Starting content engagement...")
            
            # Navigate to home timeline
            await self._ensure_on_home()
            
            # Scroll through timeline
            await self.behavior.human_scroll(self.page)
            
            # Find tweets to engage with
            tweets = await self.page.query_selector_all('article[data-testid="tweet"]')
            
            for tweet in tweets[:10]:  # Limit to first 10 tweets
                try:
                    await self._process_tweet_for_engagement(tweet)
                    await self.behavior.human_delay("general")
                except Exception as e:
                    logger.error(f"Tweet processing error: {e}")
                    continue
            
            # Refresh timeline occasionally
            if self._should_refresh_timeline():
                await self.page.reload(wait_until="networkidle")
                self.last_refresh = datetime.now()
            
        except Exception as e:
            logger.error(f"Content engagement error: {e}")
    
    async def _process_tweet_for_engagement(self, tweet_element) -> None:
        """Process individual tweet for potential engagement"""
        try:
            # Extract tweet data
            tweet_data = await self._extract_tweet_data(tweet_element)
            if not tweet_data:
                return
            
            tweet_id = tweet_data.get('id', '')
            if tweet_id in self.processed_tweets:
                return
            
            tweet_text = tweet_data.get('text', '').lower()
            author = tweet_data.get('author', '').lower()
            
            # Check if this tweet should be engaged with
            should_engage = self._should_engage_with_tweet(tweet_text, author)
            
            if should_engage:
                engagement_type = self._determine_engagement_type(author)
                await self._engage_with_tweet(tweet_element, tweet_data, engagement_type)
                
            self.processed_tweets.add(tweet_id)
            
        except Exception as e:
            logger.error(f"Tweet processing error: {e}")
    
    def _should_engage_with_tweet(self, tweet_text: str, author: str) -> bool:
        """Determine if tweet should be engaged with"""
        # Check target usernames
        target_users = [user.lower() for user in self.engagement_config.get('target_usernames', [])]
        if author in target_users:
            return True
        
        # Check keywords
        keywords = [kw.lower() for kw in self.engagement_config.get('keywords_to_like', [])]
        if any(keyword in tweet_text for keyword in keywords):
            return True
        
        return False
    
    def _determine_engagement_type(self, author: str) -> str:
        """Determine type of engagement based on author"""
        target_users = [user.lower() for user in self.engagement_config.get('target_usernames', [])]
        
        if author.lower() in target_users:
            return "full_engagement"  # Like, retweet, and reply
        else:
            return "like_only"  # Just like
    
    async def _engage_with_tweet(self, tweet_element, tweet_data: Dict, engagement_type: str) -> None:
        """Engage with a specific tweet"""
        try:
            # Like the tweet
            if self.config.can_engage_on_platform('twitter', 'like'):
                like_button = await tweet_element.query_selector('div[data-testid="like"]')
                if like_button:
                    await like_button.click()
                    await self.behavior.human_delay()
                    self.config.record_platform_action('twitter', 'like')
                    self.daily_actions['likes'] += 1
            
            if engagement_type == "full_engagement":
                # Retweet
                if self.config.can_engage_on_platform('twitter', 'retweet'):
                    retweet_button = await tweet_element.query_selector('div[data-testid="retweet"]')
                    if retweet_button:
                        await retweet_button.click()
                        await self.behavior.human_delay()
                        
                        # Confirm retweet
                        confirm_button = await self.page.wait_for_selector('div[data-testid="retweetConfirm"]', timeout=5000)
                        await confirm_button.click()
                        await self.behavior.human_delay()
                        
                        self.config.record_platform_action('twitter', 'retweet')
                        self.daily_actions['retweets'] += 1
                
                # Reply with AI-generated content
                if self.config.can_engage_on_platform('twitter', 'reply'):
                    await self._reply_to_tweet(tweet_element, tweet_data)
            
            logger.debug(f"Engaged with tweet: {engagement_type}")
            
        except Exception as e:
            logger.error(f"Tweet engagement error: {e}")
    
    async def _reply_to_tweet(self, tweet_element, tweet_data: Dict) -> None:
        """Reply to a tweet with AI-generated content"""
        try:
            # Generate intelligent reply
            original_text = tweet_data.get('text', '')
            reply_content = await self.ai_processor.generate_intelligent_reply(original_text)
            
            if not reply_content:
                logger.warning("Could not generate reply content")
                return
            
            # Click reply button
            reply_button = await tweet_element.query_selector('div[data-testid="reply"]')
            if reply_button:
                await reply_button.click()
                await self.behavior.human_delay()
                
                # Type reply
                reply_input_selector = 'div[data-testid="tweetTextarea_0"]'
                await self.behavior.human_type(self.page, reply_input_selector, reply_content)
                
                # Post reply
                reply_post_button = await self.page.wait_for_selector('div[data-testid="tweetButtonInline"]')
                await reply_post_button.click()
                
                await self.behavior.human_delay()
                
                self.config.record_platform_action('twitter', 'reply')
                self.daily_actions['replies'] += 1
                
                logger.debug(f"Replied to tweet: {reply_content[:50]}...")
        
        except Exception as e:
            logger.error(f"Reply error: {e}")
    
    async def _extract_tweet_data(self, tweet_element) -> Optional[Dict[str, Any]]:
        """Extract data from tweet element"""
        try:
            # Extract tweet text
            text_element = await tweet_element.query_selector('div[data-testid="tweetText"]')
            text = await text_element.inner_text() if text_element else ""
            
            # Extract author
            author_element = await tweet_element.query_selector('div[data-testid="User-Name"] a')
            author = ""
            if author_element:
                href = await author_element.get_attribute('href')
                if href:
                    author = href.split('/')[-1]
            
            # Extract tweet ID (simplified)
            tweet_id = f"{author}_{hash(text)}"
            
            return {
                'id': tweet_id,
                'text': text,
                'author': author,
                'element': tweet_element
            }
            
        except Exception as e:
            logger.error(f"Tweet data extraction error: {e}")
            return None
    
    async def _add_image_to_tweet(self, image_path: str) -> None:
        """Add image to tweet"""
        try:
            # Click add media button
            media_button = await self.page.wait_for_selector('div[data-testid="attachments"]')
            await media_button.click()
            await self.behavior.human_delay()
            
            # Upload image
            file_input = await self.page.wait_for_selector('input[type="file"]')
            await file_input.set_input_files(image_path)
            
            # Wait for upload to complete
            await self.behavior.human_delay("general")
            
        except Exception as e:
            logger.error(f"Image upload error: {e}")
    
    async def _ensure_on_home(self) -> None:
        """Ensure we're on the home timeline"""
        current_url = self.page.url
        if "twitter.com/home" not in current_url:
            await self.page.goto("https://twitter.com/home", wait_until="networkidle")
            await self.behavior.human_delay()
    
    def _should_refresh_timeline(self) -> bool:
        """Determine if timeline should be refreshed"""
        if not self.last_refresh:
            return True
        
        refresh_interval = self.config.get_human_behavior_config().get('refresh_interval', 300)  # 5 minutes
        return (datetime.now() - self.last_refresh).seconds > refresh_interval
    
    async def cleanup(self) -> None:
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
                
            logger.info("Twitter bot cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bot statistics"""
        return {
            'logged_in': self.logged_in,
            'session_duration': (datetime.now() - self.session_start).seconds if self.session_start else 0,
            'daily_actions': self.daily_actions.copy(),
            'processed_tweets': len(self.processed_tweets)
        }


def create_twitter_bot(config_manager: ConfigManager, ai_processor: AIProcessor) -> TwitterBot:
    """Create and configure Twitter bot"""
    return TwitterBot(config_manager, ai_processor)