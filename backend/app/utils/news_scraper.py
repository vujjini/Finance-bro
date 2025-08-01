import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.utils.logger import setup_logger
import time
from urllib.parse import urljoin, urlparse
import hashlib

logger = setup_logger(__name__)

class NewsScraperManager:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Common patterns to filter out from news content
        self.filter_patterns = [
            r'sponsored by.*',
            r'advertisement.*',
            r'related articles.*',
            r'subscribe to.*',
            r'sign up for.*',
            r'follow us on.*',
            r'©.*all rights reserved.*',
            r'terms of use.*',
            r'privacy policy.*',
            r'author:.*',
            r'contact:.*'
        ]
    
    def search_google_news(self, query: str, days: int = 7, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Google News for articles related to the query."""
        try:
            # Google News search URL
            search_url = f"https://news.google.com/search"
            params = {
                'q': query,
                'hl': 'en-US',
                'gl': 'US',
                'ceid': 'US:en'
            }
            
            response = self.session.get(search_url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = []
            
            # Parse Google News results
            for article_elem in soup.find_all('article')[:max_results]:
                try:
                    # Extract title
                    title_elem = article_elem.find('h3') or article_elem.find('h4')
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    
                    # Extract link
                    link_elem = article_elem.find('a')
                    if not link_elem or not link_elem.get('href'):
                        continue
                    
                    # Google News links are usually relative
                    link = urljoin('https://news.google.com', link_elem['href'])
                    
                    # Extract source and time
                    source = "Google News"
                    published_date = datetime.now().isoformat()
                    
                    # Try to extract more metadata
                    time_elem = article_elem.find('time')
                    if time_elem:
                        published_date = time_elem.get('datetime', published_date)
                    
                    source_elem = article_elem.find(string=re.compile(r'\w+\.\w+'))
                    if source_elem:
                        source = source_elem.strip()
                    
                    articles.append({
                        'title': title,
                        'url': link,
                        'source': source,
                        'published_date': published_date,
                        'content': ''  # Will be filled by scraping individual articles
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing article element: {str(e)}")
                    continue
            
            logger.info(f"Found {len(articles)} articles from Google News for query: {query}")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching Google News for '{query}': {str(e)}")
            return []
    
    def scrape_article_content(self, url: str) -> Optional[str]:
        """Scrape full article content from a URL."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
                element.decompose()
            
            # Try common content selectors
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content',
                '[role="main"]',
                'main',
                '.story-body',
                '.article-body'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    content = ' '.join([elem.get_text(separator=' ', strip=True) for elem in elements])
                    break
            
            # Fallback: get all paragraph text
            if not content:
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text(separator=' ', strip=True) for p in paragraphs])
            
            # Clean up the content
            content = self._clean_content(content)
            
            return content if len(content) > 100 else None
            
        except Exception as e:
            logger.warning(f"Error scraping content from {url}: {str(e)}")
            return None
    
    def _clean_content(self, content: str) -> str:
        """Clean up scraped content by removing common noise."""
        if not content:
            return ""
        
        # Apply filter patterns
        for pattern in self.filter_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        content = content.strip()
        
        # Remove very short sentences (likely noise)
        sentences = content.split('.')
        filtered_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        return '. '.join(filtered_sentences)
    
    def get_stock_news_articles(self, company_name: str, symbol: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get comprehensive news articles for a stock using multiple search strategies."""
        all_articles = []
        
        # Search strategies
        search_queries = [
            f"{symbol} stock",
            f"{company_name} earnings",
            f"{company_name} news",
            f"{symbol} analysis"
        ]
        
        seen_urls = set()
        
        for query in search_queries:
            articles = self.search_google_news(query, days=days, max_results=10)
            
            for article in articles:
                # Avoid duplicates
                url_hash = hashlib.md5(article['url'].encode()).hexdigest()
                if url_hash in seen_urls:
                    continue
                seen_urls.add(url_hash)
                
                # Scrape full content
                full_content = self.scrape_article_content(article['url'])
                if full_content:
                    article['content'] = full_content
                    all_articles.append(article)
                
                # Rate limiting
                time.sleep(1)
                
                # Limit total articles
                if len(all_articles) >= 25:
                    break
            
            if len(all_articles) >= 25:
                break
            
            # Rate limiting between searches
            time.sleep(2)
        
        logger.info(f"Scraped {len(all_articles)} articles for {company_name} ({symbol})")
        return all_articles
    
    def save_articles_to_file(self, articles: List[Dict[str, Any]], filename: str):
        """Save articles to a text file for processing."""
        try:
            with open(f"{filename}.txt", 'w', encoding='utf-8') as f:
                for article in articles:
                    f.write(f"Title: {article['title']}\n")
                    f.write(f"Source: {article['source']}\n")
                    f.write(f"URL: {article['url']}\n")
                    f.write(f"Published: {article['published_date']}\n")
                    f.write(f"Content: {article['content']}\n")
                    f.write("\n" + "="*80 + "\n\n")
            
            logger.info(f"Saved {len(articles)} articles to {filename}.txt")
            
        except Exception as e:
            logger.error(f"Error saving articles to file: {str(e)}")

def get_news_scraper() -> NewsScraperManager:
    """Get news scraper manager instance."""
    return NewsScraperManager()