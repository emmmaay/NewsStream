# Overview

This is an automated news bot system that orchestrates comprehensive news automation across multiple social media platforms. The bot subscribes to real-time news feeds using WebSub, processes content with AI for enhancement and deduplication, and automatically posts to Twitter, Facebook, and Telegram channels. The system is designed to behave like a human user with sophisticated anti-detection mechanisms and intelligent content management.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Components

**Main Orchestrator (`main.py`)**
- Central control system that coordinates all components
- Manages system state and component lifecycle
- Implements logging and error handling across the entire application

**Configuration Management (`core/config_manager.py`)**
- Centralized configuration loading from YAML/JSON files
- Platform-specific daily limits tracking (posts, likes, retweets, replies)
- Dynamic configuration updates and validation
- Rate limiting enforcement across all social platforms

**WebSub Subscriber (`core/websub_subscriber.py`)**
- Real-time news feed subscription using WebSub (PubSubHubbub) protocol
- FastAPI-based webhook server for receiving feed updates
- XML/RSS feed parsing and content extraction
- Subscription management and renewal handling

**AI Content Processor (`core/ai_processor.py`)**
- GROQ AI integration with multiple API key rotation system
- Intelligent content enhancement and response generation
- Smart failover and rate limiting for API keys
- Content processing and optimization for different platforms

**Deduplication Engine (`core/deduplication_engine.py`)**
- Advanced content similarity detection using semantic analysis
- Content fingerprinting for exact and near-duplicate detection
- Redis-based caching for performance optimization
- NLTK integration for natural language processing

## Social Media Integration

**Twitter Bot (`social/twitter_bot.py`)**
- Playwright-based browser automation for human-like behavior
- Advanced anti-detection mechanisms with realistic user simulation
- Behavior randomization for typing, scrolling, and interaction patterns
- Fake user agent rotation and human delay simulation

**Facebook Poster (`social/facebook_poster.py`)**
- Facebook Graph API integration for page posting
- Image and text content posting capabilities
- Rate limiting and quota management
- Page access token authentication

**Telegram Poster (`social/telegram_poster.py`)**
- Telegram Bot API integration for channel posting
- Media file handling and content formatting
- Channel management and broadcasting capabilities

## Design Patterns

**Factory Pattern**: Used for creating platform-specific social media components with consistent interfaces

**Observer Pattern**: WebSub subscriber notifies content processors when new feeds arrive

**Strategy Pattern**: Different AI processing strategies based on content type and platform requirements

**Circuit Breaker Pattern**: API key rotation system with failover mechanisms for resilience

**Rate Limiting**: Comprehensive rate limiting across all platforms to prevent API quota exhaustion

# External Dependencies

## AI Services
- **GROQ API**: Primary AI processing service with multiple key rotation for content enhancement and generation
- **OpenAI Tiktoken**: Token counting and text processing utilities

## Social Media APIs
- **Twitter**: Browser automation via Playwright (no official API dependency)
- **Facebook Graph API v18.0**: Page posting and content management
- **Telegram Bot API**: Channel posting and media handling

## Data Storage
- **Redis**: Content deduplication caching and session management
- **File System**: Configuration files (YAML/JSON), logs, and media storage

## Web Technologies
- **FastAPI**: WebSub webhook server for real-time feed subscriptions
- **Uvicorn**: ASGI server for running the webhook endpoint
- **aiohttp**: Async HTTP client for API communications

## Content Processing
- **NLTK**: Natural language processing for content analysis and deduplication
- **feedparser**: RSS/XML feed parsing and content extraction
- **textstat**: Content readability analysis

## Browser Automation
- **Playwright**: Headless browser automation for Twitter interactions
- **fake-useragent**: User agent rotation for anti-detection

## Utilities
- **asyncio**: Asynchronous programming foundation
- **logging**: Comprehensive logging and monitoring
- **hashlib/hmac**: Content fingerprinting and webhook verification
- **xml.etree.ElementTree**: XML parsing for feed processing