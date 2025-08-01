from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from enum import Enum

class RiskLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class RecommendationAction(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

class NewsSource(BaseModel):
    title: str
    url: str
    published_date: datetime
    source: str
    relevance_score: Optional[float] = None

class StockAnalysis(BaseModel):
    symbol: str
    company_name: str
    qualitative_analysis: str = Field(..., description="Narrative about recent news, company events, and market sentiment")
    quantitative_analysis: str = Field(..., description="Analysis of price trends, volumes, and volatility")
    user_portfolio_fit: str = Field(..., description="How well the stock aligns with user's portfolio and risk preferences")
    recommendation: str = Field(..., description="Final investment advice")
    recommendation_action: RecommendationAction
    risk_level: RiskLevel
    confidence_score: float = Field(..., ge=0, le=1)
    target_price: Optional[Decimal] = None
    news_sources: List[NewsSource] = []
    analysis_date: datetime
    
class PortfolioAnalysisRequest(BaseModel):
    portfolio_id: str
    include_recommendations: bool = True
    
class PortfolioAnalysis(BaseModel):
    portfolio_id: str
    overall_analysis: str
    risk_assessment: str
    diversification_analysis: str
    recommendations: List[str]
    individual_stocks: List[StockAnalysis]
    overall_risk_level: RiskLevel
    suggested_actions: List[str]
    analysis_date: datetime

class MarketRecommendation(BaseModel):
    symbol: str
    company_name: str
    sector: str
    recommendation_type: str = Field(..., description="forex, stocks, crypto, etc.")
    reasoning: str
    target_price: Optional[Decimal] = None
    risk_level: RiskLevel
    time_horizon: str
    confidence_score: float = Field(..., ge=0, le=1)

class ChatMessage(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str
    timestamp: datetime

class ChatSession(BaseModel):
    id: str
    user_id: str
    portfolio_id: Optional[str] = None
    stock_symbol: Optional[str] = None
    messages: List[ChatMessage] = []
    context_documents: List[str] = []  # Document IDs for RAG context
    created_at: datetime
    updated_at: datetime

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    stock_symbol: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessage
    sources: List[NewsSource] = []

class AnalysisCache(BaseModel):
    key: str
    symbol: str
    data: Dict[str, Any]
    expires_at: datetime
    created_at: datetime