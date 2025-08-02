# backend/app/routes/portfolio.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid
from datetime import datetime, timezone

from ..models.portfolio import Portfolio, PortfolioCreate, AddStockRequest
from ..models.user import User
from ..routes.auth import get_current_user

router = APIRouter()

# Temporary in-memory portfolio storage
# Create ORMs for these in memory storages as well. Can use the same ORMs when a DB service is integrated
portfolios_storage = {}
user_portfolios = {}

@router.post("/", response_model=Portfolio)
async def create_portfolio(
    portfolio_data: PortfolioCreate,
    current_user: User = Depends(get_current_user)
):
    portfolio_id = str(uuid.uuid4())
    portfolio = Portfolio(
        id=portfolio_id,
        user_id=current_user.id,
        name=portfolio_data.name,
        description=portfolio_data.description,
        stocks=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    portfolios_storage[portfolio_id] = portfolio
    
    if current_user.id not in user_portfolios:
        user_portfolios[current_user.id] = []
    user_portfolios[current_user.id].append(portfolio_id)
    
    return portfolio

@router.get("/", response_model=List[Portfolio])
async def get_user_portfolios(current_user: User = Depends(get_current_user)):
    user_portfolio_ids = user_portfolios.get(current_user.id, [])
    return [portfolios_storage[pid] for pid in user_portfolio_ids if pid in portfolios_storage]

@router.get("/{portfolio_id}", response_model=Portfolio)
async def get_portfolio(
    portfolio_id: str,
    current_user: User = Depends(get_current_user)
):
    portfolio = portfolios_storage.get(portfolio_id)
    if not portfolio or portfolio.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@router.post("/{portfolio_id}/stocks")
async def add_stock_to_portfolio(
    portfolio_id: str,
    stock_data: AddStockRequest,
    current_user: User = Depends(get_current_user)
):
    portfolio = portfolios_storage.get(portfolio_id)
    if not portfolio or portfolio.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Add stock to portfolio
    from ..models.portfolio import StockHolding
    existing_stock = next((s for s in portfolio.stocks if s.symbol == stock_data.symbol.upper()), None)
    if existing_stock:
        # Update existing stock
        existing_stock.shares += stock_data.shares
        # Optionally update purchase price or take weighted average
        if stock_data.purchase_price is not None:
            existing_stock.purchase_price = stock_data.purchase_price
            existing_stock.updated_date = datetime.now(timezone.utc)
    else:
        new_stock = StockHolding(
            symbol=stock_data.symbol.upper(),
            company_name=stock_data.company_name,
            shares=stock_data.shares,
            purchase_price=stock_data.purchase_price,
            added_date=datetime.now(timezone.utc),
            updated_date = datetime.now(timezone.utc)
        )
        portfolio.stocks.append(new_stock)
    portfolio.updated_at = datetime.now(timezone.utc)
    
    return {"message": f"Added {stock_data.shares} shares of {stock_data.symbol} to portfolio"}