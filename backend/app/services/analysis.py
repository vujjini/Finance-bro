from typing import List, Optional, Dict, Any
import os
import json
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from app.models.analysis import (
    StockAnalysis, PortfolioAnalysis, PortfolioAnalysisRequest,
    NewsSource, RiskLevel, RecommendationAction, MarketRecommendation,
    AnalysisCache
)
from app.models.portfolio import Portfolio
from app.models.user import User
from app.utils.vector_store import get_vector_store
from app.utils.polygon_client import get_polygon_client
from app.utils.news_scraper import get_news_scraper
from app.utils.logger import setup_logger
from langchain.chat_models import init_chat_model
from langchain_google_vertexai import VertexAIEmbeddings
from pydantic import BaseModel, Field
from typing_extensions import Annotated
import re

logger = setup_logger(__name__)

# Pydantic model for structured LLM output
class FinancialAnalysisOutput(BaseModel):
    qualitative_analysis: str = Field(..., description="Narrative about recent news, company events, and market sentiment")
    quantitative_analysis: str = Field(..., description="Analysis of price trends, volumes, and volatility")
    user_portfolio_fit: str = Field(..., description="How well the stock aligns with user's portfolio and risk preferences")
    recommendation: str = Field(..., description="Final investment advice")
    recommendation_action: RecommendationAction = Field(..., description="Specific recommendation action")
    risk_level: RiskLevel = Field(..., description="Risk assessment")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in the analysis")
    target_price: Optional[float] = Field(None, description="Target price if mentioned")

class AnalysisService:
    def __init__(self):
        self.vector_store = get_vector_store()
        self.polygon_client = get_polygon_client()
        self.news_scraper = get_news_scraper()
        self.cache = {}  # In-memory cache (could be Redis in production)
        self.cache_ttl = 3600  # 1 hour cache TTL
        
        # Initialize LLM
        self.llm = init_chat_model("gemini-2.0-flash-001", model_provider="google_vertexai")
        self.structured_llm = self.llm.with_structured_output(FinancialAnalysisOutput)
        
        logger.info("Analysis service initialized")
    
    async def analyze_stock(self, symbol: str, company_name: str, user: User, portfolio: Optional[Portfolio] = None) -> StockAnalysis:
        """Perform comprehensive stock analysis using RAG."""
        
        # Check cache first
        cache_key = f"stock_analysis_{symbol}_{user.id}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info(f"Returning cached analysis for {symbol}")
            return StockAnalysis(**cached_result)
        
        try:
            # Step 1: Collect and process news data
            logger.info(f"Starting analysis for {symbol} ({company_name})")
            news_sources = await self._collect_news_data(symbol, company_name)
            
            # Step 2: Get market data
            market_data = self._get_market_data(symbol)
            
            # Step 3: Process documents and add to vector store
            doc_ids = await self._process_and_store_documents(symbol, news_sources)
            
            # Step 4: Perform RAG analysis
            analysis_result = await self._perform_rag_analysis(
                symbol, company_name, user, portfolio, market_data
            )
            
            # Step 5: Create final analysis object
            stock_analysis = StockAnalysis(
                symbol=symbol,
                company_name=company_name,
                qualitative_analysis=analysis_result.qualitative_analysis,
                quantitative_analysis=analysis_result.quantitative_analysis,
                user_portfolio_fit=analysis_result.user_portfolio_fit,
                recommendation=analysis_result.recommendation,
                recommendation_action=analysis_result.recommendation_action,
                risk_level=analysis_result.risk_level,
                confidence_score=analysis_result.confidence_score,
                target_price=Decimal(str(analysis_result.target_price)) if analysis_result.target_price else None,
                news_sources=news_sources,
                analysis_date=datetime.utcnow()
            )
            
            # Cache the result
            self._cache_result(cache_key, stock_analysis.dict())
            
            logger.info(f"Completed analysis for {symbol}")
            return stock_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing stock {symbol}: {str(e)}")
            raise e
    
    async def analyze_portfolio(self, request: PortfolioAnalysisRequest, user: User, portfolio: Portfolio) -> PortfolioAnalysis:
        """Analyze an entire portfolio."""
        
        individual_analyses = []
        
        # Analyze each stock in the portfolio
        for stock_holding in portfolio.stocks:
            try:
                stock_analysis = await self.analyze_stock(
                    stock_holding.symbol,
                    stock_holding.company_name,
                    user,
                    portfolio
                )
                individual_analyses.append(stock_analysis)
            except Exception as e:
                logger.warning(f"Failed to analyze {stock_holding.symbol}: {str(e)}")
                continue
        
        # Generate overall portfolio analysis
        overall_analysis = await self._generate_portfolio_summary(portfolio, individual_analyses, user)
        
        return PortfolioAnalysis(
            portfolio_id=portfolio.id,
            overall_analysis=overall_analysis['overall'],
            risk_assessment=overall_analysis['risk'],
            diversification_analysis=overall_analysis['diversification'],
            recommendations=overall_analysis['recommendations'],
            individual_stocks=individual_analyses,
            overall_risk_level=self._calculate_overall_risk_level(individual_analyses),
            suggested_actions=overall_analysis['actions'],
            analysis_date=datetime.utcnow()
        )
    
    async def get_market_recommendations(self, recommendation_type: str = "stocks", limit: int = 5) -> List[MarketRecommendation]:
        """Get market recommendations for different asset types."""
        
        # For demo purposes, focus on popular stocks
        # In production, this could use market screeners, trending stocks, etc.
        popular_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "AMZN", "META"]
        
        recommendations = []
        
        for symbol in popular_symbols[:limit]:
            try:
                # Get basic company info
                company_details = self.polygon_client.get_company_details(symbol)
                if not company_details:
                    continue
                
                # Get recent news
                news_items = self.polygon_client.get_stock_news(symbol, days=3, limit=10)
                
                # Simple analysis for recommendations
                current_price = self.polygon_client.get_current_price(symbol)
                
                # Create a basic recommendation (this could be more sophisticated)
                recommendation = MarketRecommendation(
                    symbol=symbol,
                    company_name=company_details['name'],
                    sector=company_details.get('sector', 'Technology'),
                    recommendation_type=recommendation_type,
                    reasoning=f"Strong market position with recent positive developments. Current price: ${current_price}",
                    target_price=Decimal(str(current_price * 1.1)) if current_price else None,
                    risk_level=RiskLevel.MEDIUM,
                    time_horizon="6-12 months",
                    confidence_score=0.75
                )
                
                recommendations.append(recommendation)
                
            except Exception as e:
                logger.warning(f"Failed to generate recommendation for {symbol}: {str(e)}")
                continue
        
        return recommendations
    
    async def _collect_news_data(self, symbol: str, company_name: str) -> List[NewsSource]:
        """Collect news data from multiple sources."""
        news_sources = []
        
        try:
            # Get news from Polygon API
            polygon_news = self.polygon_client.get_stock_news(symbol, days=7, limit=20)
            for article in polygon_news:
                news_sources.append(NewsSource(
                    title=article['title'],
                    url=article['url'],
                    published_date=datetime.fromisoformat(article['published_date'].replace('Z', '+00:00')),
                    source=article['source'],
                    relevance_score=0.8
                ))
            
            # Get news from web scraping (more comprehensive content)
            scraped_articles = self.news_scraper.get_stock_news_articles(company_name, symbol, days=7)
            for article in scraped_articles:
                # Avoid duplicates
                if not any(ns.url == article['url'] for ns in news_sources):
                    news_sources.append(NewsSource(
                        title=article['title'],
                        url=article['url'],
                        published_date=datetime.fromisoformat(article['published_date']) if isinstance(article['published_date'], str) else article['published_date'],
                        source=article['source'],
                        relevance_score=0.9
                    ))
            
        except Exception as e:
            logger.warning(f"Error collecting news for {symbol}: {str(e)}")
        
        return news_sources[:25]  # Limit to top 25 articles
    
    def _get_market_data(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get market data for the stock."""
        return self.polygon_client.get_stock_data(symbol, days=days)
    
    async def _process_and_store_documents(self, symbol: str, news_sources: List[NewsSource]) -> List[str]:
        """Process news articles and store them in vector database."""
        documents = []
        
        for news_source in news_sources:
            # Create document for vector store
            doc = {
                "title": news_source.title,
                "content": f"Title: {news_source.title}\nSource: {news_source.source}\nPublished: {news_source.published_date}\nContent: {getattr(news_source, 'content', news_source.title)}",
                "url": news_source.url,
                "published_date": news_source.published_date.isoformat(),
                "source": news_source.source
            }
            documents.append(doc)
        
        # Add documents to vector store
        doc_ids = self.vector_store.add_documents(documents, symbol)
        
        logger.info(f"Stored {len(doc_ids)} documents for {symbol} in vector database")
        return doc_ids
    
    async def _perform_rag_analysis(self, symbol: str, company_name: str, user: User, portfolio: Optional[Portfolio], market_data: List[Dict[str, Any]]) -> FinancialAnalysisOutput:
        """Perform RAG-based analysis using retrieved documents and market data."""
        
        # Retrieve relevant documents
        query = f"Analysis investment recommendation {symbol} {company_name} stock market news"
        relevant_docs = self.vector_store.search_documents(query, symbol=symbol, limit=10)
        
        # Prepare context
        context_parts = []
        
        # Add news context
        for doc in relevant_docs:
            context_parts.append(f"News Article: {doc['title']}\nSource: {doc['source']}\nContent: {doc['content']}\n")
        
        # Add market data context
        if market_data:
            recent_data = market_data[-5:]  # Last 5 days
            context_parts.append("Recent Market Data:")
            for data_point in recent_data:
                context_parts.append(f"Date: {data_point['date']}, Open: ${data_point['open']}, High: ${data_point['high']}, Low: ${data_point['low']}, Close: ${data_point['close']}, Volume: {data_point['volume']}")
        
        # Build user profile context
        profile_context = self._build_user_profile_context(user, portfolio)
        
        # Create the prompt
        prompt = self._create_analysis_prompt(symbol, company_name, "\n".join(context_parts), profile_context)
        
        # Get LLM analysis
        try:
            analysis_result = self.structured_llm.invoke(prompt)
            return analysis_result
        except Exception as e:
            logger.error(f"Error getting LLM analysis: {str(e)}")
            # Fallback to basic analysis
            return self._create_fallback_analysis(symbol, company_name)
    
    def _build_user_profile_context(self, user: User, portfolio: Optional[Portfolio]) -> str:
        """Build user profile context for personalized analysis."""
        context = f"User Profile:\n"
        
        if user.profile:
            context += f"- Risk Tolerance: {user.profile.risk_tolerance}\n"
            context += f"- Investment Horizon: {user.profile.investment_horizon or 'Not specified'}\n"
            context += f"- Primary Goal: {user.profile.primary_goal}\n"
            context += f"- Liquidity Preference: {user.profile.liquidity_preference}\n"
        
        if portfolio and portfolio.stocks:
            context += f"\nCurrent Portfolio:\n"
            context += f"- Total Value: ${portfolio.total_value or 0}\n"
            context += f"- Number of Holdings: {len(portfolio.stocks)}\n"
            context += f"- Holdings: {', '.join([f'{stock.symbol} ({stock.shares} shares)' for stock in portfolio.stocks[:5]])}\n"
            
            # Sector allocation
            sectors = {}
            for stock in portfolio.stocks:
                sector = stock.sector or "Unknown"
                sectors[sector] = sectors.get(sector, 0) + 1
            context += f"- Sector Distribution: {', '.join([f'{k}: {v}' for k, v in sectors.items()])}\n"
        
        return context
    
    def _create_analysis_prompt(self, symbol: str, company_name: str, context: str, profile_context: str) -> str:
        """Create the analysis prompt for the LLM."""
        return f"""
        You are a financial advisor analyzing the stock {company_name} ({symbol}) for a specific user.

        You are provided with:
        - Recent news articles about the stock
        - Quantitative stock performance data
        - The user's portfolio profile and asset allocation

        {context}

        {profile_context}

        Task: Provide a comprehensive analysis with the following structure:

        1. **Qualitative Analysis**: Summarize sentiment, events, or outlook from recent news articles. Mention analyst opinions, product announcements, or risks.

        2. **Quantitative Analysis**: Discuss recent price trends, volume, and volatility. Mention if it's rising, falling, or fluctuating.

        3. **User Portfolio Fit**: Assess how this stock fits into the current portfolio (sector overlap, diversification). Does it increase or reduce risk? Is its weighting appropriate?

        4. **Final Recommendation**: Should the user buy, hold, or sell this stock? Justify with qualitative, quantitative, and portfolio-level reasoning.

        Also provide:
        - A specific recommendation action (strong_buy, buy, hold, sell, strong_sell)
        - Risk level assessment (very_low, low, medium, high, very_high)
        - Confidence score (0.0 to 1.0)
        - Target price if you can reasonably estimate one

        Base your analysis only on the provided information. Do not fabricate data.
        """
    
    def _create_fallback_analysis(self, symbol: str, company_name: str) -> FinancialAnalysisOutput:
        """Create a fallback analysis when LLM fails."""
        return FinancialAnalysisOutput(
            qualitative_analysis=f"Limited news data available for {company_name} ({symbol}). General market conditions should be considered.",
            quantitative_analysis=f"Recent price data for {symbol} shows normal market fluctuations. More detailed analysis requires additional data.",
            user_portfolio_fit="This stock's fit with your portfolio depends on your current holdings and diversification goals.",
            recommendation=f"Hold position in {symbol} until more comprehensive data is available for proper analysis.",
            recommendation_action=RecommendationAction.HOLD,
            risk_level=RiskLevel.MEDIUM,
            confidence_score=0.3,
            target_price=None
        )
    
    async def _generate_portfolio_summary(self, portfolio: Portfolio, analyses: List[StockAnalysis], user: User) -> Dict[str, Any]:
        """Generate overall portfolio analysis summary."""
        
        if not analyses:
            return {
                "overall": "Portfolio analysis unavailable due to insufficient stock data.",
                "risk": "Risk assessment unavailable.",
                "diversification": "Diversification analysis unavailable.",
                "recommendations": ["Add stocks to portfolio for analysis"],
                "actions": ["Build portfolio with diverse holdings"]
            }
        
        # Calculate overall metrics
        total_value = portfolio.total_value or Decimal('0')
        high_risk_count = sum(1 for a in analyses if a.risk_level in [RiskLevel.HIGH, RiskLevel.VERY_HIGH])
        buy_recommendations = sum(1 for a in analyses if a.recommendation_action in [RecommendationAction.BUY, RecommendationAction.STRONG_BUY])
        
        # Generate summary
        summary = {
            "overall": f"Portfolio contains {len(analyses)} analyzed stocks with total value of ${total_value}. {buy_recommendations} stocks show buy signals, {high_risk_count} stocks are high risk.",
            "risk": f"Portfolio risk level: {'High' if high_risk_count > len(analyses) / 2 else 'Medium' if high_risk_count > 0 else 'Low'}",
            "diversification": f"Portfolio spans {len(set(a.symbol[:2] for a in analyses))} sectors with {len(portfolio.stocks)} total holdings.",
            "recommendations": [
                f"Consider {'reducing' if high_risk_count > len(analyses) / 2 else 'maintaining'} exposure to high-risk positions",
                f"Strong buy signals detected in: {', '.join([a.symbol for a in analyses if a.recommendation_action == RecommendationAction.STRONG_BUY][:3])}" if buy_recommendations > 0 else "No strong buy signals detected",
                "Maintain diversification across sectors and asset classes"
            ],
            "actions": [
                "Review individual stock analyses for detailed recommendations",
                "Consider rebalancing if sector concentration is too high",
                "Monitor risk levels and adjust position sizes accordingly"
            ]
        }
        
        return summary
    
    def _calculate_overall_risk_level(self, analyses: List[StockAnalysis]) -> RiskLevel:
        """Calculate overall portfolio risk level."""
        if not analyses:
            return RiskLevel.MEDIUM
        
        risk_scores = {
            RiskLevel.VERY_LOW: 1,
            RiskLevel.LOW: 2,
            RiskLevel.MEDIUM: 3,
            RiskLevel.HIGH: 4,
            RiskLevel.VERY_HIGH: 5
        }
        
        avg_risk = sum(risk_scores[a.risk_level] for a in analyses) / len(analyses)
        
        if avg_risk <= 1.5:
            return RiskLevel.VERY_LOW
        elif avg_risk <= 2.5:
            return RiskLevel.LOW
        elif avg_risk <= 3.5:
            return RiskLevel.MEDIUM
        elif avg_risk <= 4.5:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH
    
    def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get item from cache if not expired."""
        if key in self.cache:
            item = self.cache[key]
            if datetime.utcnow().timestamp() - item['timestamp'] < self.cache_ttl:
                return item['data']
            else:
                del self.cache[key]
        return None
    
    def _cache_result(self, key: str, data: Dict[str, Any]):
        """Cache analysis result."""
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.utcnow().timestamp()
        }
        
        # Simple cache cleanup (remove old entries)
        if len(self.cache) > 100:
            # Remove oldest 20 entries
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1]['timestamp'])
            for old_key, _ in sorted_items[:20]:
                del self.cache[old_key]