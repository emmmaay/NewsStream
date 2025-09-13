"""
GROQ AI Integration with Multiple Key Rotation
==============================================
Handles content processing, enhancement, and intelligent response generation
"""

import asyncio
import logging
import random
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import json

import aiohttp
from groq import Groq
import tiktoken

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AIKeyRotator:
    """Manages multiple GROQ API keys with intelligent rotation and failover"""
    
    def __init__(self, api_keys: List[str]):
        # Filter out all placeholder keys and empty/invalid keys
        placeholder_patterns = ["YOUR_GROQ_KEY", "your_api_key", "placeholder", ""]
        self.api_keys = [
            key for key in api_keys 
            if key and not any(pattern in key for pattern in placeholder_patterns) and len(key) > 10
        ]
        self.current_index = 0
        self.key_status: Dict[str, Dict] = {}
        self.failed_keys = set()
        
        # Initialize key status tracking
        for key in self.api_keys:
            self.key_status[key] = {
                'success_count': 0,
                'error_count': 0,
                'last_used': None,
                'last_error': None,
                'rate_limited_until': None
            }
    
    def get_next_key(self) -> Optional[str]:
        """Get next available API key using smart rotation"""
        if not self.api_keys:
            logger.error("No valid API keys available")
            return None
        
        # Filter out rate-limited keys
        available_keys = []
        current_time = datetime.now()
        
        for key in self.api_keys:
            if key in self.failed_keys:
                continue
                
            status = self.key_status[key]
            rate_limit_until = status.get('rate_limited_until')
            
            if rate_limit_until and current_time < rate_limit_until:
                continue  # Still rate limited
                
            available_keys.append(key)
        
        if not available_keys:
            # If all keys are rate limited, use the one with earliest expiry
            logger.warning("All keys rate limited, using earliest available")
            earliest_key = min(
                self.api_keys,
                key=lambda k: self.key_status[k].get('rate_limited_until', datetime.min)
            )
            return earliest_key
        
        # Use round-robin with preference for less-used keys
        key_usage_scores = []
        for key in available_keys:
            status = self.key_status[key]
            usage_score = status['success_count'] - (status['error_count'] * 2)
            key_usage_scores.append((key, usage_score))
        
        # Sort by usage score (lower is better for rotation)
        key_usage_scores.sort(key=lambda x: x[1])
        
        # Use the least used key with some randomization
        top_keys = key_usage_scores[:min(3, len(key_usage_scores))]
        selected_key = random.choice(top_keys)[0]
        
        return selected_key
    
    def record_success(self, api_key: str):
        """Record successful API call"""
        if api_key in self.key_status:
            self.key_status[api_key]['success_count'] += 1
            self.key_status[api_key]['last_used'] = datetime.now()
            self.failed_keys.discard(api_key)  # Remove from failed keys
    
    def record_error(self, api_key: str, error_type: str, error_message: str):
        """Record API error and handle rate limiting"""
        if api_key not in self.key_status:
            return
            
        self.key_status[api_key]['error_count'] += 1
        self.key_status[api_key]['last_error'] = error_message
        
        # Handle rate limiting
        if "rate limit" in error_message.lower() or error_type == "rate_limit":
            # Rate limited for 1 hour
            self.key_status[api_key]['rate_limited_until'] = datetime.now() + timedelta(hours=1)
            logger.warning(f"API key rate limited: {api_key[:8]}...")
            
        elif "invalid" in error_message.lower() or error_type == "auth_error":
            # Invalid key - mark as failed
            self.failed_keys.add(api_key)
            logger.error(f"API key marked as failed: {api_key[:8]}...")
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get status report of all API keys"""
        return {
            'total_keys': len(self.api_keys),
            'active_keys': len(self.api_keys) - len(self.failed_keys),
            'failed_keys': len(self.failed_keys),
            'key_details': {
                key[:8] + "...": {
                    'success_count': status['success_count'],
                    'error_count': status['error_count'],
                    'last_used': status['last_used'].isoformat() if status['last_used'] else None,
                    'is_rate_limited': (
                        status.get('rate_limited_until') and 
                        datetime.now() < status['rate_limited_until']
                    ),
                    'is_failed': key in self.failed_keys
                }
                for key, status in self.key_status.items()
            }
        }


class AIProcessor:
    """Advanced AI processing system with GROQ integration"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.ai_config = config_manager.get_ai_config()
        
        # Load API keys from environment and config
        api_keys = self._load_api_keys()
        
        # Initialize key rotator
        self.key_rotator = AIKeyRotator(api_keys)
        
        # AI settings
        self.model = self.ai_config.get('model', 'mixtral-8x7b-32768')
        self.max_tokens = self.ai_config.get('max_tokens', 1000)
        self.temperature = self.ai_config.get('temperature', 0.7)
        
        # Content cache for processing optimization
        self.content_cache: Dict[str, Any] = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Initialize tokenizer for content management
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"Could not initialize tokenizer: {e}")
            self.tokenizer = None
    
    def _load_api_keys(self) -> List[str]:
        """Load and validate GROQ API keys from environment and config"""
        keys = []
        
        # First try environment variable
        env_key = os.getenv('GROQ_API_KEY')
        if env_key and len(env_key.strip()) > 10:  
            cleaned_key = env_key.strip()
            # Filter out placeholder patterns
            placeholder_patterns = ['YOUR_GROQ_KEY', 'your_api_key', 'placeholder']
            if cleaned_key not in placeholder_patterns:
                keys.append(cleaned_key)
                logger.info("✅ GROQ API key loaded from environment")
        
        # Then try config file keys
        config_keys = self.ai_config.get('primary_keys', [])
        for key in config_keys:
            if key and len(key.strip()) > 10 and key.strip() not in keys:
                cleaned_key = key.strip()
                # Filter out placeholder patterns
                placeholder_patterns = ['YOUR_GROQ_KEY', 'your_api_key', 'placeholder']
                if cleaned_key not in placeholder_patterns:
                    keys.append(cleaned_key)
        
        if not keys:
            logger.warning("❌ No valid GROQ API keys found - AI features will be disabled")
            logger.info("🔧 Add your GROQ API key to fix this: export GROQ_API_KEY=your_actual_key")
        else:
            logger.info(f"✅ Loaded {len(keys)} valid GROQ API key(s) - AI enhancement active")
            
        return keys
    
    async def enhance_content(self, original_content: str, topic: str = "") -> Optional[str]:
        """Enhance news content to make it more engaging"""
        try:
            # Create content hash for caching
            content_hash = hashlib.md5(original_content.encode()).hexdigest()
            
            # Check cache first
            if self._is_cached(content_hash, 'enhance'):
                logger.debug("Using cached enhanced content")
                return self.content_cache[content_hash]['enhanced']
            
            # Create enhancement prompt
            prompt = self._create_enhancement_prompt(original_content, topic)
            
            # Process with AI
            enhanced = await self._process_with_ai(prompt, "content_enhancement")
            
            if enhanced:
                # Cache the result
                self._cache_result(content_hash, 'enhance', {'enhanced': enhanced})
                logger.debug("Content enhanced successfully")
                return enhanced
            
            # Fallback to original content
            logger.warning("AI enhancement failed, using original content")
            return original_content
            
        except Exception as e:
            logger.error(f"Content enhancement error: {e}")
            return original_content
    
    async def generate_social_post(self, news_content: str, platform: str, topic: str = "") -> Optional[str]:
        """Generate platform-specific social media post"""
        char_limit = 280  # Default limit
        try:
            # Get platform config
            platform_config = self.config.get_twitter_config() if platform == 'twitter' else {}
            char_limit = platform_config.get('limits', {}).get('character_limit', 280)
            
            # Create content hash for caching
            cache_key = f"{platform}_{hashlib.md5(news_content.encode()).hexdigest()}"
            
            if self._is_cached(cache_key, 'social_post'):
                logger.debug("Using cached social post")
                return self.content_cache[cache_key]['post']
            
            # Create social media post prompt
            prompt = self._create_social_post_prompt(news_content, platform, char_limit, topic)
            
            # Process with AI
            social_post = await self._process_with_ai(prompt, "social_post")
            
            if social_post:
                # Cache the result
                self._cache_result(cache_key, 'social_post', {'post': social_post})
                logger.debug(f"Social post generated for {platform}")
                return social_post
            
            # Fallback to truncated original
            return self._create_fallback_post(news_content, char_limit, topic)
            
        except Exception as e:
            logger.error(f"Social post generation error: {e}")
            return self._create_fallback_post(news_content, char_limit, topic)
    
    async def generate_intelligent_reply(self, original_post: str, context: str = "") -> Optional[str]:
        """Generate intelligent reply to a social media post"""
        try:
            # Create content hash for caching
            cache_key = f"reply_{hashlib.md5((original_post + context).encode()).hexdigest()}"
            
            if self._is_cached(cache_key, 'reply'):
                logger.debug("Using cached reply")
                return self.content_cache[cache_key]['reply']
            
            # Create reply prompt
            prompt = self._create_reply_prompt(original_post, context)
            
            # Process with AI
            reply = await self._process_with_ai(prompt, "intelligent_reply")
            
            if reply:
                # Cache the result
                self._cache_result(cache_key, 'reply', {'reply': reply})
                logger.debug("Intelligent reply generated")
                return reply
            
            return None
            
        except Exception as e:
            logger.error(f"Reply generation error: {e}")
            return None
    
    async def analyze_content_quality(self, content: str) -> Dict[str, Any]:
        """Analyze content quality and sentiment"""
        try:
            # Create analysis prompt
            prompt = f"""
            Analyze this content for quality and sentiment. Return JSON format:
            {{
                "quality_score": 0.0-1.0,
                "sentiment": "positive|neutral|negative",
                "engagement_potential": 0.0-1.0,
                "topics": ["topic1", "topic2"],
                "is_tech_related": true/false,
                "content_type": "news|opinion|announcement",
                "reasons": ["reason1", "reason2"]
            }}
            
            Content: {content[:1000]}
            """
            
            # Process with AI
            analysis_result = await self._process_with_ai(prompt, "content_analysis")
            
            if analysis_result:
                try:
                    # Parse JSON response
                    analysis = json.loads(analysis_result)
                    return analysis
                except json.JSONDecodeError:
                    logger.error("Failed to parse content analysis JSON")
            
            # Fallback analysis
            return self._create_fallback_analysis(content)
            
        except Exception as e:
            logger.error(f"Content analysis error: {e}")
            return self._create_fallback_analysis(content)
    
    async def create_thread_content(self, long_content: str, platform: str) -> List[str]:
        """Break long content into platform-appropriate thread"""
        char_limit = 280  # Default limit
        try:
            platform_config = self.config.get_twitter_config() if platform == 'twitter' else {}
            char_limit = platform_config.get('limits', {}).get('character_limit', 280)
            
            # Create threading prompt
            prompt = f"""
            Break this content into a Twitter thread. Each tweet should be under {char_limit-20} characters 
            (leaving room for thread numbering). Make natural breaks that maintain context.
            Return as JSON array of strings.
            
            Content: {long_content}
            """
            
            # Process with AI
            thread_result = await self._process_with_ai(prompt, "thread_creation")
            
            if thread_result:
                try:
                    thread_posts = json.loads(thread_result)
                    if isinstance(thread_posts, list):
                        return thread_posts
                except json.JSONDecodeError:
                    pass
            
            # Fallback to simple splitting
            return self._create_simple_thread(long_content, char_limit)
            
        except Exception as e:
            logger.error(f"Thread creation error: {e}")
            return self._create_simple_thread(long_content, char_limit)
    
    async def _process_with_ai(self, prompt: str, operation_type: str) -> Optional[str]:
        """Process prompt with AI using key rotation"""
        max_retries = len(self.key_rotator.api_keys)
        
        for retry in range(max_retries):
            api_key = self.key_rotator.get_next_key()
            if not api_key:
                logger.error("No available API keys")
                return None
            
            try:
                # Initialize Groq client
                client = Groq(api_key=api_key)
                
                # Make API call
                response = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a helpful AI assistant specialized in content creation and social media."},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                # Record success
                self.key_rotator.record_success(api_key)
                
                result = response.choices[0].message.content
                return result.strip() if result else ""
                
            except Exception as e:
                error_message = str(e)
                logger.error(f"AI processing error (attempt {retry + 1}): {error_message}")
                
                # Record error
                if "rate limit" in error_message.lower():
                    self.key_rotator.record_error(api_key, "rate_limit", error_message)
                elif "invalid" in error_message.lower():
                    self.key_rotator.record_error(api_key, "auth_error", error_message)
                else:
                    self.key_rotator.record_error(api_key, "general_error", error_message)
                
                # Continue to next key
                continue
        
        logger.error(f"All API keys failed for {operation_type}")
        return None
    
    def _create_enhancement_prompt(self, content: str, topic: str) -> str:
        """Create prompt for content enhancement"""
        return f"""
        Enhance this news content to make it more engaging and professional while maintaining accuracy.
        Make it more lively and appealing for social media sharing.
        
        Topic: {topic}
        Original Content: {content}
        
        Requirements:
        - Keep all factual information accurate
        - Make it more engaging and conversational
        - Optimize for social media sharing
        - Keep it concise but informative
        - Maintain professional tone
        """
    
    def _create_social_post_prompt(self, content: str, platform: str, char_limit: int, topic: str) -> str:
        """Create prompt for social media post generation"""
        return f"""
        Create a {platform} post from this news content. 
        
        Requirements:
        - Must be under {char_limit} characters
        - Include relevant hashtags (max 3)
        - Make it engaging and shareable
        - Keep the key information
        - Use appropriate tone for {platform}
        - Topic focus: {topic}
        
        Content: {content}
        """
    
    def _create_reply_prompt(self, original_post: str, context: str) -> str:
        """Create prompt for intelligent reply generation"""
        return f"""
        Generate a thoughtful, intelligent reply to this social media post. 
        The reply should be engaging, add value, and show expertise in technology.
        
        Original Post: {original_post}
        Context: {context}
        
        Requirements:
        - Be conversational and friendly
        - Add value to the discussion
        - Show technology expertise
        - Keep under 280 characters
        - Avoid generic responses
        """
    
    def _create_fallback_post(self, content: str, char_limit: int, topic: str) -> str:
        """Create fallback social media post"""
        # Get hashtags
        hashtags = self.config.get_hashtags_for_topic(topic)
        hashtag_string = " ".join(hashtags) if hashtags else ""
        
        # Calculate available space
        available_chars = char_limit - len(hashtag_string) - 10  # Buffer
        
        # Truncate content
        if len(content) > available_chars:
            content = content[:available_chars-3] + "..."
        
        return f"{content} {hashtag_string}".strip()
    
    def _create_fallback_analysis(self, content: str) -> Dict[str, Any]:
        """Create fallback content analysis"""
        word_count = len(content.split())
        tech_keywords = ["ai", "artificial intelligence", "machine learning", "technology", "tech", "innovation"]
        
        is_tech = any(keyword in content.lower() for keyword in tech_keywords)
        
        return {
            "quality_score": 0.7 if word_count > 50 else 0.5,
            "sentiment": "neutral",
            "engagement_potential": 0.6,
            "topics": ["technology"] if is_tech else ["general"],
            "is_tech_related": is_tech,
            "content_type": "news",
            "reasons": ["Fallback analysis - AI processing unavailable"]
        }
    
    def _create_simple_thread(self, content: str, char_limit: int) -> List[str]:
        """Create simple thread by splitting content"""
        words = content.split()
        threads = []
        current_thread = ""
        
        for word in words:
            if len(current_thread + " " + word) > char_limit - 20:
                if current_thread:
                    threads.append(current_thread.strip())
                current_thread = word
            else:
                current_thread += " " + word if current_thread else word
        
        if current_thread:
            threads.append(current_thread.strip())
        
        return threads
    
    def _is_cached(self, cache_key: str, operation: str) -> bool:
        """Check if result is cached and valid"""
        if cache_key not in self.content_cache:
            return False
            
        cached_data = self.content_cache[cache_key]
        
        # Check TTL
        if datetime.now() - cached_data['timestamp'] > timedelta(seconds=self.cache_ttl):
            del self.content_cache[cache_key]
            return False
            
        return operation in cached_data
    
    def _cache_result(self, cache_key: str, operation: str, data: Dict[str, Any]):
        """Cache operation result"""
        if cache_key not in self.content_cache:
            self.content_cache[cache_key] = {'timestamp': datetime.now()}
        
        self.content_cache[cache_key].update(data)
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get AI system status"""
        return {
            'key_rotator_status': self.key_rotator.get_status_report(),
            'cache_entries': len(self.content_cache),
            'model': self.model,
            'settings': {
                'max_tokens': self.max_tokens,
                'temperature': self.temperature
            }
        }
    
    def clear_cache(self):
        """Clear content cache"""
        self.content_cache.clear()
        logger.info("Content cache cleared")


def create_ai_processor(config_manager: ConfigManager) -> AIProcessor:
    """Create and configure AI processor"""
    return AIProcessor(config_manager)