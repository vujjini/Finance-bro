from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

class StockHolding(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol")
    company_name: str = Field(..., description="Company name")
    shares: Decimal = Field(..., gt=0, description="Number of shares owned")
    purchase_price: Decimal = Field(..., gt=0, description="Average purchase price per share")
    purchase_date: datetime = Field(..., description="Date of purchase")
    sector: Optional[str] = None
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    gain_loss: Optional[Decimal] = None
    gain_loss_percentage: Optional[Decimal] = None

class Portfolio(BaseModel):
    id: str
    user_id: str
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    stocks: List[StockHolding] = []
    total_value: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    total_gain_loss: Optional[Decimal] = None
    total_gain_loss_percentage: Optional[Decimal] = None
    created_at: datetime
    updated_at: datetime

class PortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None

class PortfolioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class StockHoldingCreate(BaseModel):
    symbol: str = Field(..., description="Stock ticker symbol")
    company_name: str = Field(..., description="Company name")
    shares: Decimal = Field(..., gt=0)
    purchase_price: Decimal = Field(..., gt=0)
    purchase_date: datetime
    sector: Optional[str] = None

class StockHoldingUpdate(BaseModel):
    shares: Optional[Decimal] = Field(None, gt=0)
    purchase_price: Optional[Decimal] = Field(None, gt=0)
    purchase_date: Optional[datetime] = None
    sector: Optional[str] = None

class PortfolioSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    total_value: Optional[Decimal] = None
    total_stocks: int
    total_gain_loss_percentage: Optional[Decimal] = None
    updated_at: datetime

class PortfolioAnalytics(BaseModel):
    portfolio_id: str
    total_value: Decimal
    total_cost: Decimal
    total_gain_loss: Decimal
    total_gain_loss_percentage: Decimal
    sector_allocation: Dict[str, Decimal]
    top_performers: List[StockHolding]
    worst_performers: List[StockHolding]
    risk_score: Optional[Decimal] = None
    diversification_score: Optional[Decimal] = None