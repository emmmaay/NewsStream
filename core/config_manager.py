"""
Configuration Manager for Automated News Bot
============================================
Handles all configuration loading, validation, and dynamic updates
"""

import yaml
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PlatformLimits:
    """Platform-specific daily limits"""
    max_posts_per_day: int
    max_likes_per_day: int = 0
    max_retweets_per_day: int = 0
    max_replies_per_day: int = 0
    current_posts: int = field(default=0)
    current_likes: int = field(default=0)
    current_retweets: int = field(default=0)
    current_replies: int = field(default=0)
    
    def can_post(self) -> bool:
        return self.current_posts < self.max_posts_per_day
    
    def can_like(self) -> bool:
        return self.current_likes < self.max_likes_per_day
    
    def can_retweet(self) -> bool:
        return self.current_retweets < self.max_retweets_per_day
    
    def can_reply(self) -> bool:
        return self.current_replies < self.max_replies_per_day
    
    def increment_posts(self):
        self.current_posts += 1
        
    def increment_likes(self):
        self.current_likes += 1
        
    def increment_retweets(self):
        self.current_retweets += 1
        
    def increment_replies(self):
        self.current_replies += 1
    
    def reset_daily_counts(self):
        self.current_posts = 0
        self.current_likes = 0
        self.current_retweets = 0
        self.current_replies = 0


class ConfigManager:
    """Comprehensive configuration management system"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.platform_limits: Dict[str, PlatformLimits] = {}
        self.emergency_stop = False
        self.load_config()
        self.setup_platform_limits()
        
    def load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Configuration file {self.config_path} not found")
                
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                
            logger.info(f"Configuration loaded from {self.config_path}")
            self._validate_config()
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def _validate_config(self) -> None:
        """Validate configuration structure and required fields"""
        required_sections = ['ai', 'news_sources', 'twitter', 'facebook', 'telegram', 'content']
        
        for section in required_sections:
            if section not in self.config:
                raise ValueError(f"Missing required configuration section: {section}")
                
        # Validate AI keys
        ai_keys = self.config['ai'].get('primary_keys', [])
        if not ai_keys:
            raise ValueError("No AI primary keys configured")
            
        # Check for placeholder patterns
        placeholder_patterns = ["YOUR_GROQ_KEY", "GROQ_API_KEY", "your_api_key", ""]
        valid_keys = [
            key for key in ai_keys 
            if key and not any(pattern in key for pattern in placeholder_patterns) and len(key) > 20
        ]
        
        if not valid_keys:
            logger.warning("AI keys not configured - using placeholder values")
        else:
            logger.info(f"Found {len(valid_keys)} valid AI keys")
            
        logger.info("Configuration validation completed successfully")
    
    def setup_platform_limits(self) -> None:
        """Initialize platform-specific daily limits"""
        # Twitter limits
        twitter_config = self.config.get('twitter', {}).get('limits', {})
        self.platform_limits['twitter'] = PlatformLimits(
            max_posts_per_day=twitter_config.get('max_posts_per_day', 50),
            max_likes_per_day=twitter_config.get('max_likes_per_day', 100),
            max_retweets_per_day=twitter_config.get('max_retweets_per_day', 30),
            max_replies_per_day=twitter_config.get('max_replies_per_day', 25)
        )
        
        # Facebook limits
        facebook_config = self.config.get('facebook', {}).get('limits', {})
        self.platform_limits['facebook'] = PlatformLimits(
            max_posts_per_day=facebook_config.get('max_posts_per_day', 10)
        )
        
        # Telegram limits
        telegram_config = self.config.get('telegram', {}).get('limits', {})
        self.platform_limits['telegram'] = PlatformLimits(
            max_posts_per_day=telegram_config.get('max_posts_per_day', 100)
        )
        
        logger.info("Platform limits initialized successfully")
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration with key rotation"""
        return self.config.get('ai', {})
    
    def get_twitter_config(self) -> Dict[str, Any]:
        """Get Twitter configuration"""
        return self.config.get('twitter', {})
    
    def get_facebook_config(self) -> Dict[str, Any]:
        """Get Facebook configuration"""
        return self.config.get('facebook', {})
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """Get Telegram configuration"""
        return self.config.get('telegram', {})
    
    def get_news_sources_config(self) -> Dict[str, Any]:
        """Get news sources configuration"""
        return self.config.get('news_sources', {})
    
    def get_content_config(self) -> Dict[str, Any]:
        """Get content processing configuration"""
        return self.config.get('content', {})
    
    def get_deduplication_config(self) -> Dict[str, Any]:
        """Get deduplication configuration"""
        return self.config.get('deduplication', {})
    
    def get_websub_config(self) -> Dict[str, Any]:
        """Get WebSub server configuration"""
        return self.config.get('websub', {})
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.config.get('database', {})
    
    def get_error_handling_config(self) -> Dict[str, Any]:
        """Get error handling configuration"""
        return self.config.get('error_handling', {})
    
    def get_platform_limits(self, platform: str) -> Optional[PlatformLimits]:
        """Get platform-specific limits"""
        return self.platform_limits.get(platform)
    
    def can_post_to_platform(self, platform: str) -> bool:
        """Check if posting is allowed on platform"""
        if self.emergency_stop:
            return False
        
        limits = self.get_platform_limits(platform)
        return limits.can_post() if limits else False
    
    def can_engage_on_platform(self, platform: str, action: str) -> bool:
        """Check if engagement action is allowed on platform"""
        if self.emergency_stop:
            return False
            
        limits = self.get_platform_limits(platform)
        if not limits:
            return False
            
        action_methods = {
            'like': limits.can_like,
            'retweet': limits.can_retweet,
            'reply': limits.can_reply
        }
        
        method = action_methods.get(action)
        return method() if method else False
    
    def record_platform_action(self, platform: str, action: str) -> None:
        """Record platform action for limit tracking"""
        limits = self.get_platform_limits(platform)
        if not limits:
            return
            
        action_methods = {
            'post': limits.increment_posts,
            'like': limits.increment_likes,
            'retweet': limits.increment_retweets,
            'reply': limits.increment_replies
        }
        
        method = action_methods.get(action)
        if method:
            method()
            logger.debug(f"Recorded {action} action for {platform}")
    
    def reset_daily_limits(self) -> None:
        """Reset all daily limits for new day"""
        for platform_limits in self.platform_limits.values():
            platform_limits.reset_daily_counts()
        logger.info("Daily limits reset for all platforms")
    
    def trigger_emergency_stop(self, reason: str = "") -> None:
        """Trigger emergency stop for all operations"""
        self.emergency_stop = True
        logger.critical(f"EMERGENCY STOP TRIGGERED: {reason}")
    
    def release_emergency_stop(self) -> None:
        """Release emergency stop"""
        self.emergency_stop = False
        logger.info("Emergency stop released")
    
    def is_emergency_stopped(self) -> bool:
        """Check if emergency stop is active"""
        return self.emergency_stop
    
    def update_niche_keywords(self, new_keywords: List[str]) -> None:
        """Dynamically update niche keywords for customization"""
        self.config['twitter']['engagement']['keywords_to_like'] = new_keywords
        logger.info(f"Updated keywords to: {new_keywords}")
    
    def update_target_usernames(self, new_usernames: List[str]) -> None:
        """Dynamically update target usernames"""
        self.config['twitter']['engagement']['target_usernames'] = new_usernames
        logger.info(f"Updated target usernames to: {new_usernames}")
    
    def save_config(self) -> None:
        """Save current configuration back to file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
    
    def get_hashtags_for_topic(self, topic: str) -> List[str]:
        """Get appropriate hashtags for a topic"""
        hashtag_config = self.get_content_config().get('hashtags', {})
        max_hashtags = hashtag_config.get('max_hashtags', 3)
        
        # Topic-specific hashtags
        if 'ai' in topic.lower() or 'artificial' in topic.lower() or 'machine learning' in topic.lower():
            hashtags = hashtag_config.get('ai_related', [])
        elif 'blockchain' in topic.lower() or 'crypto' in topic.lower():
            hashtags = hashtag_config.get('blockchain', [])
        elif 'cloud' in topic.lower():
            hashtags = hashtag_config.get('cloud', [])
        elif 'security' in topic.lower() or 'cyber' in topic.lower():
            hashtags = hashtag_config.get('security', [])
        else:
            hashtags = hashtag_config.get('general', [])
        
        # Limit number of hashtags
        return hashtags[:max_hashtags]
    
    def get_human_behavior_config(self) -> Dict[str, Any]:
        """Get human-like behavior configuration for Twitter"""
        return self.get_twitter_config().get('behavior', {})
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        logger.info("Reloading configuration...")
        self.load_config()
        self.setup_platform_limits()
        logger.info("Configuration reloaded successfully")