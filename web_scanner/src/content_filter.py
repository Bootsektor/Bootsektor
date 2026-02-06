import logging
import re
from typing import Dict, Any, List

class ContentFilter:
    """Content filtering and relevance detection"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Load filter configuration
        self.keywords = config.get('content_filter.keywords', [])
        self.blacklist = config.get('content_filter.blacklist', [])
        self.min_content_length = config.get('content_filter.min_content_length', 100)
        self.learning_enabled = config.get('content_filter.learning_enabled', True)
        
        # Compile regex patterns for performance
        self.keyword_patterns = [re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE) 
                                 for keyword in self.keywords]
        self.blacklist_patterns = [re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE) 
                                   for term in self.blacklist]
    
    async def is_relevant(self, article: Dict[str, Any]) -> bool:
        """Check if article is relevant based on filtering criteria"""
        try:
            title = article.get('title', '').lower()
            content = article.get('content', '').lower()
            combined_text = f"{title} {content}"
            
            # Check minimum content length
            if len(combined_text) < self.min_content_length:
                return False
            
            # Check blacklist
            if self._contains_blacklisted_terms(combined_text):
                return False
            
            # Check keywords
            if not self._contains_keywords(combined_text):
                return False
            
            # Additional relevance checks
            return self._additional_relevance_checks(article)
            
        except Exception as e:
            self.logger.error(f"Error in relevance check: {e}")
            return False
    
    def _contains_keywords(self, text: str) -> bool:
        """Check if text contains any keywords"""
        if not self.keywords:
            return True  # No keywords specified, accept all
        
        for pattern in self.keyword_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _contains_blacklisted_terms(self, text: str) -> bool:
        """Check if text contains blacklisted terms"""
        for pattern in self.blacklist_patterns:
            if pattern.search(text):
                return True
        return False
    
    def _additional_relevance_checks(self, article: Dict[str, Any]) -> bool:
        """Additional relevance checks"""
        # Check for spam indicators
        title = article.get('title', '')
        content = article.get('content', '')
        
        # Title too short or too long
        if len(title) < 10 or len(title) > 200:
            return False
        
        # Content quality checks
        if self._is_low_quality_content(content):
            return False
        
        # Check for excessive capitalization (spam indicator)
        if sum(1 for c in title if c.isupper()) / len(title) > 0.3:
            return False
        
        return True
    
    def _is_low_quality_content(self, content: str) -> bool:
        """Check for low quality content indicators"""
        # Check for repetitive content
        words = content.lower().split()
        if len(words) < 20:
            return True
        
        # Check word diversity
        unique_words = set(words)
        if len(unique_words) / len(words) < 0.3:
            return True
        
        # Check for excessive punctuation
        punctuation_count = sum(1 for c in content if c in '!?')
        if punctuation_count / len(content) > 0.05:
            return True
        
        return False
    
    async def is_high_priority(self, article: Dict[str, Any]) -> bool:
        """Check if article should be high priority for notifications"""
        try:
            title = article.get('title', '').lower()
            content = article.get('content', '').lower()
            combined_text = f"{title} {content}"
            
            # High priority keywords
            high_priority_keywords = [
                'urgent', 'breaking', 'alert', 'important', 
                'critical', 'emergency', 'update', 'announcement'
            ]
            
            for keyword in high_priority_keywords:
                if keyword in combined_text:
                    return True
            
            # Check for recent timestamps
            if self._is_recent_content(article):
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in priority check: {e}")
            return False
    
    def _is_recent_content(self, article: Dict[str, Any]) -> bool:
        """Check if content is recent"""
        from datetime import datetime, timedelta
        
        scraped_at = article.get('scraped_at')
        if scraped_at:
            try:
                scrape_time = datetime.fromisoformat(scraped_at.replace('Z', '+00:00'))
                return datetime.now() - scrape_time < timedelta(hours=24)
            except:
                pass
        
        return False
    
    def calculate_relevance_score(self, article: Dict[str, Any]) -> float:
        """Calculate relevance score (0.0 to 1.0)"""
        try:
            title = article.get('title', '')
            content = article.get('content', '')
            combined_text = f"{title} {content}".lower()
            
            score = 0.0
            
            # Keyword matching
            keyword_matches = sum(1 for pattern in self.keyword_patterns 
                                if pattern.search(combined_text))
            if self.keywords:
                score += (keyword_matches / len(self.keywords)) * 0.4
            
            # Content length score
            content_length = len(combined_text)
            if content_length >= self.min_content_length:
                length_score = min(content_length / 1000, 1.0) * 0.2
                score += length_score
            
            # Quality score
            quality_score = 0.3
            if self._is_low_quality_content(content):
                quality_score = 0.0
            score += quality_score
            
            # Recency score
            if self._is_recent_content(article):
                score += 0.1
            
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating relevance score: {e}")
            return 0.0
    
    def update_keywords(self, new_keywords: List[str]):
        """Update keywords for filtering"""
        self.keywords = new_keywords
        self.keyword_patterns = [re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE) 
                                for keyword in self.keywords]
        self.logger.info(f"Updated keywords: {new_keywords}")
    
    def update_blacklist(self, new_blacklist: List[str]):
        """Update blacklist terms"""
        self.blacklist = new_blacklist
        self.blacklist_patterns = [re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE) 
                                  for term in self.blacklist]
        self.logger.info(f"Updated blacklist: {new_blacklist}")