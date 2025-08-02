# backend/app/models/portfolio.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class StockHolding(BaseModel):
    symbol: str
    company_name: str
    shares: float
    purchase_price: Optional[float] = None
    added_date: datetime
    updated_date: datetime

class PortfolioBase(BaseModel):
    name: str
    description: Optional[str] = None

class PortfolioCreate(PortfolioBase):
    pass

class Portfolio(PortfolioBase):
    id: str
    user_id: str
    stocks: List[StockHolding] = []
    created_at: datetime
    updated_at: datetime

class AddStockRequest(BaseModel):
    symbol: str
    company_name: str
    shares: float
    purchase_price: Optional[float] = None