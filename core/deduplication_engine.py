"""
Smart Deduplication Engine
==========================
Advanced content deduplication using similarity analysis and semantic comparison
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from difflib import SequenceMatcher
import asyncio
import json

import redis
from textstat import flesch_reading_ease
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import nltk

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ContentFingerprint:
    """Create and manage content fingerprints for deduplication"""
    
    def __init__(self):
        self.stemmer = PorterStemmer()
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            self.stopwords = set(stopwords.words('english'))
        except Exception as e:
            logger.warning(f"NLTK setup issue: {e}")
            self.stopwords = set()
    
    def create_content_hash(self, content: str) -> str:
        """Create content hash for exact duplicate detection"""
        # Normalize content
        normalized = self._normalize_content(content)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def create_semantic_fingerprint(self, content: str) -> Dict[str, Any]:
        """Create semantic fingerprint for similarity detection"""
        try:
            # Extract key features
            words = self._extract_key_words(content)
            sentences = self._extract_key_sentences(content)
            
            # Create fingerprint
            fingerprint = {
                'key_words': words,
                'key_sentences': sentences,
                'word_count': len(content.split()),
                'sentence_count': len(sent_tokenize(content)),
                'reading_ease': flesch_reading_ease(content) if content.strip() else 0,
                'content_structure': self._analyze_structure(content),
                'topic_indicators': self._extract_topic_indicators(content)
            }
            
            return fingerprint
            
        except Exception as e:
            logger.error(f"Semantic fingerprint creation error: {e}")
            return self._create_basic_fingerprint(content)
    
    def _normalize_content(self, content: str) -> str:
        """Normalize content for consistent hashing"""
        # Remove extra whitespace and normalize case
        content = ' '.join(content.lower().split())
        
        # Remove common variations
        content = content.replace('\n', ' ').replace('\t', ' ')
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace(''', "'").replace(''', "'")
        
        return content.strip()
    
    def _extract_key_words(self, content: str) -> List[str]:
        """Extract key words from content"""
        try:
            words = word_tokenize(content.lower())
            
            # Filter out stopwords and short words
            key_words = [
                self.stemmer.stem(word) 
                for word in words 
                if (word.isalpha() and 
                    len(word) > 3 and 
                    word not in self.stopwords)
            ]
            
            # Return most frequent words
            word_freq = {}
            for word in key_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Sort by frequency and return top words
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            return [word for word, freq in sorted_words[:20]]
            
        except Exception as e:
            logger.error(f"Key word extraction error: {e}")
            return content.lower().split()[:20]
    
    def _extract_key_sentences(self, content: str) -> List[str]:
        """Extract key sentences from content"""
        try:
            sentences = sent_tokenize(content)
            
            # Score sentences by length and position
            scored_sentences = []
            for i, sentence in enumerate(sentences):
                words = len(sentence.split())
                position_score = 1.0 / (i + 1)  # Earlier sentences score higher
                length_score = min(words / 20.0, 1.0)  # Optimal length around 20 words
                
                total_score = position_score + length_score
                scored_sentences.append((sentence.strip(), total_score))
            
            # Sort by score and return top sentences
            scored_sentences.sort(key=lambda x: x[1], reverse=True)
            return [sent for sent, score in scored_sentences[:5]]
            
        except Exception as e:
            logger.error(f"Key sentence extraction error: {e}")
            return content.split('.')[:5]
    
    def _analyze_structure(self, content: str) -> Dict[str, Any]:
        """Analyze content structure"""
        try:
            paragraphs = content.split('\n\n')
            sentences = sent_tokenize(content)
            words = content.split()
            
            return {
                'paragraph_count': len(paragraphs),
                'avg_paragraph_length': sum(len(p.split()) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
                'sentence_count': len(sentences),
                'avg_sentence_length': sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0,
                'word_count': len(words),
                'has_quotes': '"' in content or "'" in content,
                'has_numbers': any(char.isdigit() for char in content),
                'has_links': 'http' in content.lower() or 'www' in content.lower()
            }
            
        except Exception as e:
            logger.error(f"Structure analysis error: {e}")
            return {'word_count': len(content.split())}
    
    def _extract_topic_indicators(self, content: str) -> List[str]:
        """Extract topic indicators from content"""
        tech_indicators = [
            'ai', 'artificial intelligence', 'machine learning', 'deep learning',
            'neural network', 'automation', 'robot', 'blockchain', 'cryptocurrency',
            'bitcoin', 'ethereum', 'cloud computing', 'aws', 'azure', 'google cloud',
            'cybersecurity', 'hacker', 'data breach', 'privacy', 'gdpr',
            'startup', 'funding', 'venture capital', 'ipo', 'acquisition',
            'software', 'app', 'mobile', 'web', 'internet', 'tech', 'technology',
            'innovation', 'digital', 'platform', 'api', 'database', 'server'
        ]
        
        content_lower = content.lower()
        found_indicators = [
            indicator for indicator in tech_indicators 
            if indicator in content_lower
        ]
        
        return found_indicators[:10]  # Limit to top 10
    
    def _create_basic_fingerprint(self, content: str) -> Dict[str, Any]:
        """Create basic fingerprint as fallback"""
        words = content.split()
        return {
            'key_words': words[:20],
            'key_sentences': content.split('.')[:3],
            'word_count': len(words),
            'sentence_count': content.count('.') + content.count('!') + content.count('?'),
            'reading_ease': 50,  # Default middle value
            'content_structure': {'word_count': len(words)},
            'topic_indicators': []
        }


class DeduplicationEngine:
    """Advanced deduplication system with multiple detection strategies"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.dedup_config = config_manager.get_deduplication_config()
        
        # Initialize components
        self.fingerprinter = ContentFingerprint()
        
        # Configuration
        self.similarity_threshold = self.dedup_config.get('similarity_threshold', 0.8)
        self.time_window_hours = self.dedup_config.get('time_window_hours', 24)
        self.content_hash_enabled = self.dedup_config.get('content_hash_enabled', True)
        self.semantic_analysis = self.dedup_config.get('semantic_analysis', True)
        
        # Initialize Redis for caching
        self.redis_client = None
        self._init_redis()
        
        # In-memory cache as fallback
        self.content_hashes: Set[str] = set()
        self.content_fingerprints: Dict[str, Dict] = {}
        self.processed_items: Dict[str, datetime] = {}
        
        logger.info("Deduplication engine initialized")
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            db_config = self.config.get_database_config().get('redis', {})
            self.redis_client = redis.Redis(
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', 6379),
                db=db_config.get('db', 0),
                password=db_config.get('password'),
                decode_responses=True
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            self.redis_client = None
    
    async def is_duplicate(self, content: str, title: str = "", url: str = "") -> Tuple[bool, str, float]:
        """
        Check if content is a duplicate
        Returns: (is_duplicate, reason, similarity_score)
        """
        try:
            # Clean expired entries first
            await self._clean_expired_entries()
            
            # Create unique identifier
            content_id = f"{title}_{url}_{content[:100]}"
            
            # 1. Exact hash duplicate check
            if self.content_hash_enabled:
                content_hash = self.fingerprinter.create_content_hash(content)
                
                if await self._is_hash_duplicate(content_hash):
                    logger.debug("Exact duplicate detected via hash")
                    return True, "exact_duplicate", 1.0
                
                # Store hash for future checks
                await self._store_content_hash(content_hash, content_id)
            
            # 2. Semantic similarity check
            if self.semantic_analysis:
                fingerprint = self.fingerprinter.create_semantic_fingerprint(content)
                
                similarity_result = await self._check_semantic_similarity(fingerprint, content_id)
                if similarity_result[0]:
                    logger.debug(f"Semantic duplicate detected: {similarity_result[2]:.2f} similarity")
                    return similarity_result
                
                # Store fingerprint for future checks
                await self._store_fingerprint(content_id, fingerprint)
            
            # 3. URL-based duplicate check
            if url:
                if await self._is_url_duplicate(url):
                    logger.debug("URL duplicate detected")
                    return True, "url_duplicate", 0.9
                
                await self._store_processed_url(url, content_id)
            
            # Not a duplicate
            await self._record_processed_item(content_id)
            return False, "unique", 0.0
            
        except Exception as e:
            logger.error(f"Duplicate detection error: {e}")
            # Fail safe - allow content through on error
            return False, "error_fallback", 0.0
    
    async def _is_hash_duplicate(self, content_hash: str) -> bool:
        """Check if content hash already exists"""
        try:
            if self.redis_client:
                return await asyncio.to_thread(
                    self.redis_client.exists, f"hash:{content_hash}"
                )
            else:
                return content_hash in self.content_hashes
                
        except Exception as e:
            logger.error(f"Hash duplicate check error: {e}")
            return False
    
    async def _store_content_hash(self, content_hash: str, content_id: str):
        """Store content hash with expiration"""
        try:
            expire_seconds = self.time_window_hours * 3600
            
            if self.redis_client:
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"hash:{content_hash}",
                    expire_seconds,
                    content_id
                )
            else:
                self.content_hashes.add(content_hash)
                
        except Exception as e:
            logger.error(f"Hash storage error: {e}")
    
    async def _check_semantic_similarity(self, fingerprint: Dict, content_id: str) -> Tuple[bool, str, float]:
        """Check semantic similarity against stored fingerprints"""
        try:
            stored_fingerprints = await self._get_stored_fingerprints()
            
            max_similarity = 0.0
            most_similar_id = ""
            
            for stored_id, stored_fingerprint in stored_fingerprints.items():
                similarity = self._calculate_similarity(fingerprint, stored_fingerprint)
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    most_similar_id = stored_id
                    
                    if similarity >= self.similarity_threshold:
                        return True, f"semantic_similar_to_{stored_id}", similarity
            
            return False, "semantically_unique", max_similarity
            
        except Exception as e:
            logger.error(f"Semantic similarity check error: {e}")
            return False, "similarity_error", 0.0
    
    def _calculate_similarity(self, fp1: Dict, fp2: Dict) -> float:
        """Calculate similarity between two fingerprints"""
        try:
            # Calculate component similarities
            word_sim = self._calculate_word_similarity(fp1.get('key_words', []), fp2.get('key_words', []))
            sentence_sim = self._calculate_sentence_similarity(fp1.get('key_sentences', []), fp2.get('key_sentences', []))
            topic_sim = self._calculate_topic_similarity(fp1.get('topic_indicators', []), fp2.get('topic_indicators', []))
            structure_sim = self._calculate_structure_similarity(fp1.get('content_structure', {}), fp2.get('content_structure', {}))
            
            # Weighted combination
            total_similarity = (
                word_sim * 0.4 +
                sentence_sim * 0.3 +
                topic_sim * 0.2 +
                structure_sim * 0.1
            )
            
            return total_similarity
            
        except Exception as e:
            logger.error(f"Similarity calculation error: {e}")
            return 0.0
    
    def _calculate_word_similarity(self, words1: List[str], words2: List[str]) -> float:
        """Calculate word overlap similarity"""
        if not words1 or not words2:
            return 0.0
            
        set1, set2 = set(words1), set(words2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_sentence_similarity(self, sentences1: List[str], sentences2: List[str]) -> float:
        """Calculate sentence similarity using SequenceMatcher"""
        if not sentences1 or not sentences2:
            return 0.0
        
        max_similarity = 0.0
        
        for s1 in sentences1:
            for s2 in sentences2:
                similarity = SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _calculate_topic_similarity(self, topics1: List[str], topics2: List[str]) -> float:
        """Calculate topic indicator similarity"""
        if not topics1 or not topics2:
            return 0.0
            
        set1, set2 = set(topics1), set(topics2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_structure_similarity(self, struct1: Dict, struct2: Dict) -> float:
        """Calculate structural similarity"""
        if not struct1 or not struct2:
            return 0.0
        
        word_count_diff = abs(struct1.get('word_count', 0) - struct2.get('word_count', 0))
        max_words = max(struct1.get('word_count', 1), struct2.get('word_count', 1))
        
        # Similarity based on word count difference (smaller difference = higher similarity)
        return 1.0 - (word_count_diff / max_words)
    
    async def _store_fingerprint(self, content_id: str, fingerprint: Dict):
        """Store content fingerprint"""
        try:
            expire_seconds = self.time_window_hours * 3600
            fingerprint_data = json.dumps(fingerprint)
            
            if self.redis_client:
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"fingerprint:{content_id}",
                    expire_seconds,
                    fingerprint_data
                )
            else:
                self.content_fingerprints[content_id] = fingerprint
                
        except Exception as e:
            logger.error(f"Fingerprint storage error: {e}")
    
    async def _get_stored_fingerprints(self) -> Dict[str, Dict]:
        """Get all stored fingerprints"""
        try:
            if self.redis_client:
                keys = await asyncio.to_thread(
                    self.redis_client.keys, "fingerprint:*"
                )
                
                fingerprints = {}
                for key in keys:
                    data = await asyncio.to_thread(self.redis_client.get, key)
                    if data:
                        content_id = key.split(':', 1)[1]
                        fingerprints[content_id] = json.loads(data)
                        
                return fingerprints
            else:
                return self.content_fingerprints.copy()
                
        except Exception as e:
            logger.error(f"Fingerprint retrieval error: {e}")
            return {}
    
    async def _is_url_duplicate(self, url: str) -> bool:
        """Check if URL has been processed"""
        try:
            if self.redis_client:
                return await asyncio.to_thread(
                    self.redis_client.exists, f"url:{hashlib.md5(url.encode()).hexdigest()}"
                )
            else:
                url_hash = hashlib.md5(url.encode()).hexdigest()
                return url_hash in self.processed_items
                
        except Exception as e:
            logger.error(f"URL duplicate check error: {e}")
            return False
    
    async def _store_processed_url(self, url: str, content_id: str):
        """Store processed URL"""
        try:
            url_hash = hashlib.md5(url.encode()).hexdigest()
            expire_seconds = self.time_window_hours * 3600
            
            if self.redis_client:
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"url:{url_hash}",
                    expire_seconds,
                    content_id
                )
            else:
                self.processed_items[url_hash] = datetime.now()
                
        except Exception as e:
            logger.error(f"URL storage error: {e}")
    
    async def _record_processed_item(self, content_id: str):
        """Record that an item has been processed"""
        try:
            expire_seconds = self.time_window_hours * 3600
            
            if self.redis_client:
                await asyncio.to_thread(
                    self.redis_client.setex,
                    f"processed:{content_id}",
                    expire_seconds,
                    datetime.now().isoformat()
                )
                
        except Exception as e:
            logger.error(f"Processed item recording error: {e}")
    
    async def _clean_expired_entries(self):
        """Clean expired entries from in-memory cache"""
        if not self.redis_client:  # Only need to clean in-memory cache
            try:
                current_time = datetime.now()
                expired_keys = [
                    key for key, timestamp in self.processed_items.items()
                    if current_time - timestamp > timedelta(hours=self.time_window_hours)
                ]
                
                for key in expired_keys:
                    del self.processed_items[key]
                
                # Also clean fingerprints (simplified cleanup)
                if len(self.content_fingerprints) > 10000:  # Arbitrary limit
                    # Remove oldest half
                    keys_to_remove = list(self.content_fingerprints.keys())[:5000]
                    for key in keys_to_remove:
                        del self.content_fingerprints[key]
                        
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics"""
        try:
            if self.redis_client:
                hash_count = self.redis_client.eval("return #redis.call('keys', 'hash:*')", 0)
                fingerprint_count = self.redis_client.eval("return #redis.call('keys', 'fingerprint:*')", 0)
                url_count = self.redis_client.eval("return #redis.call('keys', 'url:*')", 0)
            else:
                hash_count = len(self.content_hashes)
                fingerprint_count = len(self.content_fingerprints)
                url_count = len(self.processed_items)
            
            return {
                'stored_hashes': hash_count,
                'stored_fingerprints': fingerprint_count,
                'processed_urls': url_count,
                'similarity_threshold': self.similarity_threshold,
                'time_window_hours': self.time_window_hours,
                'redis_available': self.redis_client is not None
            }
            
        except Exception as e:
            logger.error(f"Stats retrieval error: {e}")
            return {'error': str(e)}
    
    async def clear_cache(self):
        """Clear deduplication cache"""
        try:
            if self.redis_client:
                # Clear Redis keys
                keys = await asyncio.to_thread(self.redis_client.keys, "hash:*")
                keys.extend(await asyncio.to_thread(self.redis_client.keys, "fingerprint:*"))
                keys.extend(await asyncio.to_thread(self.redis_client.keys, "url:*"))
                keys.extend(await asyncio.to_thread(self.redis_client.keys, "processed:*"))
                
                if keys:
                    await asyncio.to_thread(self.redis_client.delete, *keys)
            
            # Clear in-memory cache
            self.content_hashes.clear()
            self.content_fingerprints.clear()
            self.processed_items.clear()
            
            logger.info("Deduplication cache cleared")
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")


def create_deduplication_engine(config_manager: ConfigManager) -> DeduplicationEngine:
    """Create and configure deduplication engine"""
    return DeduplicationEngine(config_manager)