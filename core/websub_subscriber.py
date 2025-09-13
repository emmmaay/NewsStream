"""
WebSub (PubSubHubbub) Subscriber System
======================================
Real-time news feed subscription system for instant content delivery
"""

import asyncio
import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from urllib.parse import urlencode, urlparse
import xml.etree.ElementTree as ET

import aiohttp
import feedparser
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import PlainTextResponse
import uvicorn

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class WebSubSubscriber:
    """WebSub subscriber for real-time news feed updates"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.websub_config = config_manager.get_websub_config()
        self.news_config = config_manager.get_news_sources_config()
        
        self.app = FastAPI(title="News Bot WebSub Subscriber")
        self.subscriptions: Dict[str, Dict] = {}
        self.callback_handlers: List[Callable] = []
        
        # Setup routes
        self.setup_routes()
        
        # Subscription tracking
        self.active_subscriptions = set()
        self.subscription_expires = {}
        
    def setup_routes(self):
        """Setup FastAPI routes for WebSub callbacks"""
        
        @self.app.get("/webhook/{feed_id}")
        async def webhook_verification(feed_id: str, request: Request):
            """Handle WebSub subscription verification"""
            try:
                hub_challenge = request.query_params.get("hub.challenge")
                hub_mode = request.query_params.get("hub.mode")
                hub_topic = request.query_params.get("hub.topic")
                hub_verify_token = request.query_params.get("hub.verify_token")
                
                # Verify token
                expected_token = self.websub_config.get('verify_token', 'default_token')
                if hub_verify_token != expected_token:
                    logger.error(f"Invalid verify token for {feed_id}")
                    raise HTTPException(status_code=403, detail="Invalid verify token")
                
                if hub_mode == "subscribe":
                    logger.info(f"Subscription verified for {feed_id}: {hub_topic}")
                    self.active_subscriptions.add(feed_id)
                    
                    # Set expiration (default 7 days)
                    expire_time = datetime.now() + timedelta(days=7)
                    self.subscription_expires[feed_id] = expire_time
                    
                elif hub_mode == "unsubscribe":
                    logger.info(f"Unsubscription verified for {feed_id}: {hub_topic}")
                    self.active_subscriptions.discard(feed_id)
                    self.subscription_expires.pop(feed_id, None)
                
                return PlainTextResponse(hub_challenge)
                
            except Exception as e:
                logger.error(f"WebSub verification error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.post("/webhook/{feed_id}")
        async def webhook_notification(feed_id: str, request: Request, background_tasks: BackgroundTasks):
            """Handle WebSub content notifications"""
            try:
                content = await request.body()
                content_type = request.headers.get("content-type", "")
                
                # Verify signature if provided
                signature = request.headers.get("x-hub-signature") or request.headers.get("x-hub-signature-256")
                if signature:
                    if not self._verify_signature(content, signature):
                        logger.error(f"Invalid signature for {feed_id}")
                        raise HTTPException(status_code=403, detail="Invalid signature")
                
                # Process content in background
                background_tasks.add_task(self._process_notification, feed_id, content.decode('utf-8'))
                
                logger.debug(f"Notification received for {feed_id}")
                return {"status": "received"}
                
            except Exception as e:
                logger.error(f"WebSub notification error: {e}")
                raise HTTPException(status_code=400, detail=str(e))
    
    def _verify_signature(self, content: bytes, signature: str) -> bool:
        """Verify WebSub signature"""
        try:
            # Extract algorithm and signature
            if signature.startswith('sha256='):
                algorithm = 'sha256'
                provided_signature = signature[7:]
            elif signature.startswith('sha1='):
                algorithm = 'sha1'
                provided_signature = signature[5:]
            else:
                return False
            
            # Calculate expected signature
            secret = self.websub_config.get('verify_token', '').encode('utf-8')
            if algorithm == 'sha256':
                expected = hmac.new(secret, content, hashlib.sha256).hexdigest()
            else:
                expected = hmac.new(secret, content, hashlib.sha1).hexdigest()
            
            return hmac.compare_digest(provided_signature, expected)
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    async def _process_notification(self, feed_id: str, content: str):
        """Process received notification content"""
        try:
            # Parse RSS/Atom content
            feed = feedparser.parse(content)
            
            if not feed.entries:
                logger.debug(f"No new entries in notification for {feed_id}")
                return
            
            logger.info(f"Processing {len(feed.entries)} new entries from {feed_id}")
            
            # Process each entry
            for entry in feed.entries:
                news_item = self._extract_news_item(entry, feed_id)
                
                # Notify all registered handlers
                for handler in self.callback_handlers:
                    try:
                        await handler(news_item)
                    except Exception as e:
                        logger.error(f"Handler error for {feed_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Content processing error for {feed_id}: {e}")
    
    def _extract_news_item(self, entry, feed_id: str) -> Dict[str, Any]:
        """Extract news item from feed entry"""
        # Get published time
        published = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            from time import mktime
            published = datetime.fromtimestamp(mktime(entry.published_parsed))
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            from time import mktime
            published = datetime.fromtimestamp(mktime(entry.updated_parsed))
        else:
            published = datetime.now()
        
        # Extract image if available
        image_url = None
        if hasattr(entry, 'media_content') and entry.media_content:
            image_url = entry.media_content[0].get('url')
        elif hasattr(entry, 'enclosures') and entry.enclosures:
            for enclosure in entry.enclosures:
                if enclosure.type.startswith('image/'):
                    image_url = enclosure.href
                    break
        
        # Extract content
        content = ""
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].value
        elif hasattr(entry, 'summary'):
            content = entry.summary
        elif hasattr(entry, 'description'):
            content = entry.description
        
        return {
            'id': getattr(entry, 'id', entry.link),
            'title': getattr(entry, 'title', ''),
            'link': getattr(entry, 'link', ''),
            'content': content,
            'summary': getattr(entry, 'summary', ''),
            'published': published,
            'author': getattr(entry, 'author', ''),
            'tags': [tag.term for tag in getattr(entry, 'tags', [])],
            'image_url': image_url,
            'source': feed_id,
            'source_title': getattr(entry, 'feed', {}).get('title', feed_id)
        }
    
    def add_callback_handler(self, handler: Callable):
        """Add callback handler for new content"""
        self.callback_handlers.append(handler)
        logger.info(f"Added callback handler: {handler.__name__}")
    
    async def subscribe_to_feeds(self):
        """Subscribe to all configured news feeds"""
        try:
            # Subscribe to Google News topics
            google_config = self.news_config.get('google_news', {})
            if google_config.get('enabled'):
                await self._subscribe_google_news(google_config)
            
            # Subscribe to TechCrunch
            techcrunch_config = self.news_config.get('techcrunch', {})
            if techcrunch_config.get('enabled'):
                await self._subscribe_to_feed(
                    'techcrunch',
                    techcrunch_config['rss_url'],
                    techcrunch_config['websub_hub']
                )
            
            # Subscribe to additional sources
            additional_sources = self.news_config.get('additional_sources', [])
            for source in additional_sources:
                await self._subscribe_to_feed(
                    source['name'].lower().replace(' ', '_'),
                    source['rss_url'],
                    source['websub_hub']
                )
                
            logger.info(f"WebSub subscriptions initiated for {len(self.subscriptions)} feeds")
            
        except Exception as e:
            logger.error(f"Subscription error: {e}")
            raise
    
    async def _subscribe_google_news(self, config: Dict):
        """Subscribe to Google News topic feeds"""
        base_url = config.get('base_url', 'https://news.google.com/rss/search')
        hub_url = config.get('websub_hub', 'https://pubsubhubbub.appspot.com/')
        topics = config.get('topics', [])
        
        for topic in topics:
            feed_id = f"google_news_{topic.lower().replace(' ', '_')}"
            topic_url = f"{base_url}?q={topic.replace(' ', '%20')}&hl=en&gl=US&ceid=US:en"
            
            await self._subscribe_to_feed(feed_id, topic_url, hub_url)
    
    async def _subscribe_to_feed(self, feed_id: str, topic_url: str, hub_url: str):
        """Subscribe to a specific feed"""
        try:
            callback_url = f"{self.websub_config['callback_url_base']}/webhook/{feed_id}"
            verify_token = self.websub_config.get('verify_token', 'default_token')
            
            subscription_data = {
                'hub.callback': callback_url,
                'hub.mode': 'subscribe',
                'hub.topic': topic_url,
                'hub.verify': 'async',
                'hub.verify_token': verify_token,
                'hub.lease_seconds': '604800'  # 7 days
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(hub_url, data=subscription_data) as response:
                    if response.status in [202, 204]:
                        self.subscriptions[feed_id] = {
                            'topic_url': topic_url,
                            'hub_url': hub_url,
                            'callback_url': callback_url,
                            'subscribed_at': datetime.now()
                        }
                        logger.info(f"Subscription request sent for {feed_id}")
                    else:
                        logger.error(f"Subscription failed for {feed_id}: {response.status}")
                        
        except Exception as e:
            logger.error(f"Subscription error for {feed_id}: {e}")
    
    async def unsubscribe_from_feed(self, feed_id: str):
        """Unsubscribe from a specific feed"""
        try:
            if feed_id not in self.subscriptions:
                logger.warning(f"Feed {feed_id} not found in subscriptions")
                return
                
            subscription = self.subscriptions[feed_id]
            callback_url = subscription['callback_url']
            topic_url = subscription['topic_url']
            hub_url = subscription['hub_url']
            verify_token = self.websub_config.get('verify_token', 'default_token')
            
            unsubscription_data = {
                'hub.callback': callback_url,
                'hub.mode': 'unsubscribe',
                'hub.topic': topic_url,
                'hub.verify': 'async',
                'hub.verify_token': verify_token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(hub_url, data=unsubscription_data) as response:
                    if response.status in [202, 204]:
                        logger.info(f"Unsubscription request sent for {feed_id}")
                    else:
                        logger.error(f"Unsubscription failed for {feed_id}: {response.status}")
                        
        except Exception as e:
            logger.error(f"Unsubscription error for {feed_id}: {e}")
    
    async def refresh_subscriptions(self):
        """Refresh expiring subscriptions"""
        try:
            current_time = datetime.now()
            
            for feed_id, expire_time in list(self.subscription_expires.items()):
                # Refresh if expiring within 24 hours
                if expire_time - current_time < timedelta(hours=24):
                    subscription = self.subscriptions.get(feed_id)
                    if subscription:
                        await self._subscribe_to_feed(
                            feed_id,
                            subscription['topic_url'],
                            subscription['hub_url']
                        )
                        
            logger.info("Subscription refresh check completed")
            
        except Exception as e:
            logger.error(f"Subscription refresh error: {e}")
    
    def get_subscription_status(self) -> Dict[str, Any]:
        """Get status of all subscriptions"""
        return {
            'active_subscriptions': len(self.active_subscriptions),
            'total_subscriptions': len(self.subscriptions),
            'subscriptions': {
                feed_id: {
                    'active': feed_id in self.active_subscriptions,
                    'expires': self.subscription_expires.get(feed_id),
                    **details
                }
                for feed_id, details in self.subscriptions.items()
            }
        }
    
    async def start_server(self):
        """Start the WebSub server"""
        try:
            host = self.websub_config.get('host', '0.0.0.0')
            port = self.websub_config.get('port', 8000)
            
            logger.info(f"Starting WebSub server on {host}:{port}")
            
            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level="info"
            )
            
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            logger.error(f"Server start error: {e}")
            raise
    
    async def fallback_feed_polling(self):
        """Fallback RSS polling for feeds without WebSub support"""
        try:
            logger.info("Starting fallback RSS polling for feeds without WebSub")
            polling_active = True
            
            # This runs as a backup for feeds that don't support WebSub
            while True:
                feeds_to_poll = 0
                
                for feed_id, subscription in self.subscriptions.items():
                    if feed_id not in self.active_subscriptions:
                        # Poll this feed since WebSub isn't working
                        await self._poll_feed(feed_id, subscription['topic_url'])
                        feeds_to_poll += 1
                
                # If we have no active WebSub subscriptions, poll all configured feeds
                if len(self.active_subscriptions) == 0:
                    logger.info("No active WebSub subscriptions - activating RSS polling fallback")
                    await self._poll_all_configured_feeds()
                
                if feeds_to_poll > 0:
                    logger.debug(f"Polled {feeds_to_poll} feeds via fallback RSS")
                
                # Poll every 10 minutes as fallback (with some jitter)
                import random
                await asyncio.sleep(600 + random.randint(0, 120))
                
        except Exception as e:
            logger.error(f"Fallback polling error: {e}")
    
    async def _poll_feed(self, feed_id: str, feed_url: str):
        """Poll a single feed for updates"""
        try:
            headers = {'User-Agent': 'NewsBot/1.0 (+https://example.com/bot)'}
            timeout = aiohttp.ClientTimeout(total=30)
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(feed_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        await self._process_notification(feed_id, content)
                    else:
                        logger.warning(f"Feed polling failed for {feed_id}: HTTP {response.status}")
                        
        except Exception as e:
            logger.error(f"Feed polling error for {feed_id}: {e}")
    
    async def _poll_all_configured_feeds(self):
        """Poll all configured feeds as fallback when WebSub fails"""
        try:
            logger.info("🔄 RSS fallback polling activated - ensuring bulletproof operation")
            feeds_polled = 0
            
            # Poll Google News topics directly
            google_config = self.news_config.get('google_news', {})
            if google_config.get('enabled'):
                base_url = google_config.get('base_url', 'https://news.google.com/rss/search')
                topics = google_config.get('topics', [])[:5]  # Limit to first 5 topics to avoid rate limits
                
                for topic in topics:
                    feed_id = f"google_news_{topic.lower().replace(' ', '_')}"
                    topic_url = f"{base_url}?q={topic.replace(' ', '%20')}&hl=en&gl=US&ceid=US:en"
                    logger.info(f"📡 Polling RSS feed: {topic}")
                    await self._poll_feed(feed_id, topic_url)
                    feeds_polled += 1
                    await asyncio.sleep(2)  # Small delay between requests
                    
            # Poll other configured sources
            additional_sources = self.news_config.get('additional_sources', [])[:3]  # Limit sources
            for source in additional_sources:
                feed_id = source['name'].lower().replace(' ', '_')
                logger.info(f"📡 Polling RSS feed: {source['name']}")
                await self._poll_feed(feed_id, source['rss_url'])
                feeds_polled += 1
                await asyncio.sleep(2)
            
            logger.info(f"✅ RSS polling completed - {feeds_polled} feeds processed (bulletproof system active)")
                
        except Exception as e:
            logger.error(f"RSS fallback polling error: {e}")


# Initialize WebSub subscriber
def create_websub_subscriber(config_manager: ConfigManager) -> WebSubSubscriber:
    """Create and configure WebSub subscriber"""
    return WebSubSubscriber(config_manager)