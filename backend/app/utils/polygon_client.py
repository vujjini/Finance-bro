from polygon import RESTClient
from typing import List, Dict, Any, Optional
import os
from datetime import datetime, timedelta
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class PolygonClientManager:
    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable is required")
        self.client = RESTClient(self.api_key)
    
    def get_stock_data(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get stock aggregates data for the specified number of days."""
        end_date = datetime.today()
        start_date = end_date - timedelta(days=days)
        
        try:
            aggs = []
            for agg in self.client.list_aggs(
                symbol,
                1,
                "day",
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                adjusted="true",
                sort="asc",
                limit=120,
            ):
                aggs.append({
                    "timestamp": agg.timestamp,
                    "open": agg.open,
                    "high": agg.high,
                    "low": agg.low,
                    "close": agg.close,
                    "volume": agg.volume,
                    "vwap": getattr(agg, "vwap", None),
                    "transactions": getattr(agg, "transactions", None),
                    "date": datetime.fromtimestamp(agg.timestamp / 1000).strftime('%Y-%m-%d')
                })
            
            logger.info(f"Retrieved {len(aggs)} data points for {symbol}")
            return aggs
            
        except Exception as e:
            logger.error(f"Error fetching stock data for {symbol}: {str(e)}")
            return []
    
    def get_stock_news(self, symbol: str, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent news for a stock symbol."""
        try:
            news_items = []
            # Get news from Polygon
            news_response = self.client.list_ticker_news(
                ticker=symbol,
                limit=limit
            )
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for article in news_response:
                published_date = datetime.fromisoformat(article.published_utc.replace('Z', '+00:00'))
                
                if published_date >= cutoff_date:
                    news_items.append({
                        "title": article.title,
                        "description": getattr(article, "description", ""),
                        "url": article.article_url,
                        "published_date": published_date.isoformat(),
                        "source": getattr(article, "publisher", {}).get("name", "Unknown"),
                        "content": getattr(article, "description", "")  # Polygon doesn't provide full content
                    })
            
            logger.info(f"Retrieved {len(news_items)} news articles for {symbol}")
            return news_items
            
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {str(e)}")
            return []
    
    def get_company_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get company details for a symbol."""
        try:
            details = self.client.get_ticker_details(symbol)
            return {
                "symbol": details.ticker,
                "name": details.name,
                "description": getattr(details, "description", ""),
                "sector": getattr(details, "sic_description", ""),
                "market_cap": getattr(details, "market_cap", None),
                "employees": getattr(details, "total_employees", None),
                "website": getattr(details, "homepage_url", ""),
            }
        except Exception as e:
            logger.error(f"Error fetching company details for {symbol}: {str(e)}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the current/latest price for a symbol."""
        try:
            # Get the most recent trading day data
            end_date = datetime.today()
            start_date = end_date - timedelta(days=7)  # Look back a week to ensure we get data
            
            aggs = list(self.client.list_aggs(
                symbol,
                1,
                "day",
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                adjusted="true",
                sort="desc",
                limit=1,
            ))
            
            if aggs:
                return float(aggs[0].close)
            return None
            
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {str(e)}")
            return None
    
    def search_symbols(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stock symbols matching a query."""
        try:
            results = []
            tickers = self.client.list_tickers(
                search=query,
                limit=limit,
                active=True
            )
            
            for ticker in tickers:
                results.append({
                    "symbol": ticker.ticker,
                    "name": getattr(ticker, "name", ""),
                    "market": getattr(ticker, "market", ""),
                    "type": getattr(ticker, "type", ""),
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching symbols for query '{query}': {str(e)}")
            return []

def get_polygon_client() -> PolygonClientManager:
    """Get Polygon client manager instance."""
    return PolygonClientManager()