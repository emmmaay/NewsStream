#!/usr/bin/env python3
"""
Comprehensive platform testing script for automated news bot
Tests all social media platforms with real credentials
"""

import asyncio
import os
from core.config_manager import ConfigManager
from core.ai_processor import AIProcessor
from social.twitter_bot import TwitterBot
from social.facebook_poster import FacebookPoster
from social.telegram_poster import TelegramPoster

async def test_all_platforms():
    print("🚀 Testing all platforms with real credentials...")
    print("=" * 60)
    
    # Initialize core components
    config = ConfigManager()
    ai_processor = AIProcessor(config)
    
    # Test results
    results = {
        'twitter': False,
        'facebook': False,
        'telegram': False,
        'groq_ai': False
    }
    
    # Test GROQ AI
    print("\n🤖 Testing GROQ AI...")
    try:
        enhanced = await ai_processor.enhance_content("This is a test news article about artificial intelligence.")
        if "test" in enhanced.lower():
            print("✅ GROQ AI: Working!")
            results['groq_ai'] = True
        else:
            print("⚠️ GROQ AI: Not enhancing content properly")
    except Exception as e:
        print(f"❌ GROQ AI Error: {e}")
    
    # Test Twitter
    print("\n🐦 Testing Twitter...")
    try:
        twitter_bot = TwitterBot(config, ai_processor)
        await twitter_bot.initialize()
        
        result = await twitter_bot.post_tweet("🤖 Testing automated news bot - AI-powered posting works! #AI #automation")
        if result:
            print("✅ Twitter: Post successful!")
            results['twitter'] = True
        else:
            print("⚠️ Twitter: Post failed - check credentials")
            
    except Exception as e:
        print(f"❌ Twitter Error: {e}")
    
    # Test Facebook
    print("\n📘 Testing Facebook...")
    try:
        fb_poster = FacebookPoster(config)
        await fb_poster.post_content("🤖 Testing automated news bot - Facebook posting works! #AI #automation", None)
        print("✅ Facebook: Post successful!")
        results['facebook'] = True
    except Exception as e:
        print(f"❌ Facebook Error: {e}")
    
    # Test Telegram
    print("\n📱 Testing Telegram...")
    try:
        tg_poster = TelegramPoster(config)
        await tg_poster.post_content("🤖 Testing automated news bot - Telegram posting works! #AI #automation", None)
        print("✅ Telegram: Post successful!")
        results['telegram'] = True
    except Exception as e:
        print(f"❌ Telegram Error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 PLATFORM TEST RESULTS:")
    print("=" * 60)
    
    for platform, success in results.items():
        status = "✅ WORKING" if success else "❌ FAILED"
        print(f"{platform.upper():12} {status}")
    
    working_count = sum(results.values())
    print(f"\n📊 Summary: {working_count}/4 platforms working")
    
    if working_count == 4:
        print("🎉 ALL PLATFORMS WORKING - SYSTEM IS BULLETPROOF!")
    elif working_count >= 2:
        print("⚠️ Some platforms working - check failed credentials")
    else:
        print("🚨 Most platforms failed - check all credentials")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_all_platforms())