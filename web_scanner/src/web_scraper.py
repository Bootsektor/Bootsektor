import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup

class WebScraper:
    """Web scraper with TOR support and content extraction"""
    
    def __init__(self, config, tor_manager, content_filter, image_processor, learning_db, notifier):
        self.config = config
        self.tor_manager = tor_manager
        self.content_filter = content_filter
        self.image_processor = image_processor
        self.learning_db = learning_db
        self.notifier = notifier
        self.logger = logging.getLogger(__name__)
        self.session = None
    
    async def start(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
    
    async def stop(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def scan_websites(self):
        """Scan all configured websites"""
        websites = self.config.get('websites', [])
        results = []
        
        for website in websites:
            try:
                articles = await self.scrape_website(website)
                filtered_articles = await self.filter_articles(articles)
                
                for article in filtered_articles:
                    # Process and download media
                    processed_article = await self.process_article(article)
                    if processed_article:
                        results.append(processed_article)
                        
                        # Create summary image
                        summary_image = await self.create_summary_image(processed_article)
                        
                        # Send notification if interesting
                        if await self.is_interesting(processed_article):
                            await self.notifier.send_notification(processed_article, summary_image)
                        
                        # Update learning database
                        await self.learning_db.record_article(processed_article)
                
            except Exception as e:
                self.logger.error(f"Error scanning website {website.get('url')}: {e}")
        
        return results
    
    async def scrape_website(self, website: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape articles from a single website"""
        url = website['url']
        selectors = website.get('selectors', {})
        
        try:
            # Get proxies from TOR manager
            proxies = self.tor_manager.get_proxies()
            
            # Use requests for scraping (more reliable than aiohttp for some sites)
            response = requests.get(url, proxies=proxies, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = []
            
            # Find article elements
            article_elements = soup.select(selectors.get('articles', 'article'))
            
            for element in article_elements:
                try:
                    article = await self.extract_article_data(element, url, selectors)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.warning(f"Error extracting article: {e}")
                    continue
            
            self.logger.info(f"Found {len(articles)} articles on {url}")
            return articles
            
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return []
    
    async def extract_article_data(self, element, base_url: str, selectors: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract article data from HTML element"""
        try:
            # Extract title
            title_elem = element.select_one(selectors.get('title', 'h1, h2, .title'))
            title = title_elem.get_text(strip=True) if title_elem else ""
            
            # Extract content
            content_elem = element.select_one(selectors.get('content', '.content, p'))
            content = content_elem.get_text(strip=True) if content_elem else ""
            
            # Extract image
            img_elem = element.select_one(selectors.get('image', 'img'))
            img_src = img_elem.get('src') if img_elem else ""
            if img_src:
                img_src = urljoin(base_url, img_src)
            
            # Extract link
            link_elem = element.select_one(selectors.get('link', 'a'))
            link = link_elem.get('href') if link_elem else ""
            if link:
                link = urljoin(base_url, link)
            
            # Skip if essential data is missing
            if not title or not content:
                return None
            
            return {
                'title': title,
                'content': content,
                'image_url': img_src,
                'link': link,
                'scraped_at': datetime.now().isoformat(),
                'source_url': base_url
            }
            
        except Exception as e:
            self.logger.error(f"Error extracting article data: {e}")
            return None
    
    async def filter_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter articles based on content criteria"""
        filtered = []
        
        for article in articles:
            if await self.content_filter.is_relevant(article):
                filtered.append(article)
        
        self.logger.info(f"Filtered to {len(filtered)} relevant articles")
        return filtered
    
    async def process_article(self, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process article - download media, clean content"""
        try:
            processed = article.copy()
            
            # Download and process image if available
            if article.get('image_url'):
                processed['local_image_path'] = await self.download_image(article['image_url'])
            
            # Clean content
            processed['cleaned_content'] = self.clean_content(article['content'])
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Error processing article: {e}")
            return None
    
    async def download_image(self, image_url: str) -> Optional[str]:
        """Download image from URL"""
        try:
            import os
            from pathlib import Path
            
            # Create images directory
            img_dir = Path("data/images")
            img_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(image_url) % 10000}.jpg"
            filepath = img_dir / filename
            
            # Download image
            proxies = self.tor_manager.get_proxies()
            response = requests.get(image_url, proxies=proxies, timeout=30, stream=True)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Error downloading image {image_url}: {e}")
            return None
    
    def clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove HTML entities
        content = re.sub(r'&[a-zA-Z0-9#]+;', '', content)
        
        # Remove special characters but keep basic punctuation
        content = re.sub(r'[^\w\s\.\,\!\?\-\:\;]', '', content)
        
        return content.strip()
    
    async def create_summary_image(self, article: Dict[str, Any]) -> Optional[str]:
        """Create summary image with headline and featured image"""
        try:
            return await self.image_processor.create_summary(article)
        except Exception as e:
            self.logger.error(f"Error creating summary image: {e}")
            return None
    
    async def is_interesting(self, article: Dict[str, Any]) -> bool:
        """Determine if article is interesting enough for notification"""
        try:
            # Use learning database to predict interest
            return await self.learning_db.predict_interest(article)
        except Exception as e:
            self.logger.error(f"Error predicting interest: {e}")
            # Fallback to basic content filtering
            return await self.content_filter.is_high_priority(article)