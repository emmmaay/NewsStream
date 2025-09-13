"""
Facebook Page Posting Integration
=================================
Posts content to Facebook pages using Graph API
"""

import logging
from typing import Dict, List, Optional, Any
import aiohttp
import aiofiles
import os

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class FacebookPoster:
    """Facebook page posting automation"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.fb_config = config_manager.get_facebook_config()
        
        self.access_token = self.fb_config.get('page_access_token', '')
        self.page_id = self.fb_config.get('page_id', '')
        self.base_url = "https://graph.facebook.com/v18.0"
        
    async def post_content(self, content: str, image_path: Optional[str] = None) -> bool:
        """Post content to Facebook page"""
        try:
            if not self.access_token or not self.page_id:
                logger.error("Facebook credentials not configured")
                return False
            
            # Check daily limits
            if not self.config.can_post_to_platform('facebook'):
                logger.warning("Daily post limit reached for Facebook")
                return False
            
            logger.info(f"Posting to Facebook: {content[:50]}...")
            
            # Post with or without image
            if image_path and os.path.exists(image_path):
                return await self._post_with_image(content, image_path)
            else:
                return await self._post_text_only(content)
                
        except Exception as e:
            logger.error(f"Facebook posting error: {e}")
            return False
    
    async def _post_text_only(self, content: str) -> bool:
        """Post text-only content"""
        try:
            url = f"{self.base_url}/{self.page_id}/feed"
            
            data = {
                'message': content,
                'access_token': self.access_token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        post_id = result.get('id', '')
                        
                        self.config.record_platform_action('facebook', 'post')
                        logger.info(f"Facebook post successful: {post_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Facebook API error: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Facebook text post error: {e}")
            return False
    
    async def _post_with_image(self, content: str, image_path: str) -> bool:
        """Post content with image"""
        try:
            # First, upload the image
            photo_id = await self._upload_image(image_path)
            if not photo_id:
                logger.warning("Image upload failed, posting text only")
                return await self._post_text_only(content)
            
            # Post with uploaded image
            url = f"{self.base_url}/{self.page_id}/feed"
            
            data = {
                'message': content,
                'attached_media[0]': f'{{"media_fbid":"{photo_id}"}}',
                'access_token': self.access_token
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        post_id = result.get('id', '')
                        
                        self.config.record_platform_action('facebook', 'post')
                        logger.info(f"Facebook post with image successful: {post_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Facebook API error: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Facebook image post error: {e}")
            return False
    
    async def _upload_image(self, image_path: str) -> Optional[str]:
        """Upload image to Facebook and return media ID"""
        try:
            url = f"{self.base_url}/{self.page_id}/photos"
            
            async with aiofiles.open(image_path, 'rb') as f:
                image_data = await f.read()
            
            data = aiohttp.FormData()
            data.add_field('access_token', self.access_token)
            data.add_field('published', 'false')  # Upload but don't publish
            data.add_field('source', image_data, filename=os.path.basename(image_path))
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        photo_id = result.get('id', '')
                        logger.debug(f"Image uploaded to Facebook: {photo_id}")
                        return photo_id
                    else:
                        error_text = await response.text()
                        logger.error(f"Facebook image upload error: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Image upload error: {e}")
            return None


def create_facebook_poster(config_manager: ConfigManager) -> FacebookPoster:
    """Create and configure Facebook poster"""
    return FacebookPoster(config_manager)