from typing import List, Optional, Dict, Any
from decimal import Decimal
import uuid
from datetime import datetime
from app.models.portfolio import (
    Portfolio, PortfolioCreate, PortfolioUpdate, StockHolding, 
    StockHoldingCreate, StockHoldingUpdate, PortfolioSummary, PortfolioAnalytics
)
from app.services.user_storage import PortfolioStorageService
from app.utils.polygon_client import get_polygon_client
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class PortfolioService:
    def __init__(self):
        self.storage = PortfolioStorageService()
        self.polygon_client = get_polygon_client()
    
    async def create_portfolio(self, user_id: str, portfolio_data: PortfolioCreate) -> Portfolio:
        """Create a new portfolio for a user."""
        portfolio_id = str(uuid.uuid4())
        return await self.storage.create_portfolio(user_id, portfolio_id, portfolio_data)
    
    async def get_user_portfolios(self, user_id: str) -> List[PortfolioSummary]:
        """Get all portfolios for a user with summary information."""
        portfolios = await self.storage.get_user_portfolios(user_id)
        summaries = []
        
        for portfolio in portfolios:
            # Calculate current values
            await self._update_portfolio_values(portfolio)
            
            summary = PortfolioSummary(
                id=portfolio.id,
                name=portfolio.name,
                description=portfolio.description,
                total_value=portfolio.total_value,
                total_stocks=len(portfolio.stocks),
                total_gain_loss_percentage=portfolio.total_gain_loss_percentage,
                updated_at=portfolio.updated_at
            )
            summaries.append(summary)
        
        return summaries
    
    async def get_portfolio(self, user_id: str, portfolio_id: str) -> Optional[Portfolio]:
        """Get a specific portfolio with updated values."""
        portfolio = await self.storage.get_portfolio(user_id, portfolio_id)
        if portfolio:
            await self._update_portfolio_values(portfolio)
            # Save updated values
            await self.storage.update_portfolio(user_id, portfolio_id, {
                'total_value': portfolio.total_value,
                'total_cost': portfolio.total_cost,
                'total_gain_loss': portfolio.total_gain_loss,
                'total_gain_loss_percentage': portfolio.total_gain_loss_percentage,
                'stocks': [stock.dict() for stock in portfolio.stocks]
            })
        return portfolio
    
    async def update_portfolio(self, user_id: str, portfolio_id: str, portfolio_update: PortfolioUpdate) -> Optional[Portfolio]:
        """Update portfolio information."""
        updates = {}
        if portfolio_update.name:
            updates['name'] = portfolio_update.name
        if portfolio_update.description is not None:
            updates['description'] = portfolio_update.description
        
        return await self.storage.update_portfolio(user_id, portfolio_id, updates)
    
    async def delete_portfolio(self, user_id: str, portfolio_id: str) -> bool:
        """Delete a portfolio."""
        return await self.storage.delete_portfolio(user_id, portfolio_id)
    
    async def add_stock_to_portfolio(self, user_id: str, portfolio_id: str, stock_data: StockHoldingCreate) -> Optional[Portfolio]:
        """Add a stock to a portfolio."""
        portfolio = await self.storage.get_portfolio(user_id, portfolio_id)
        if not portfolio:
            return None
        
        # Get current price and company details
        current_price = self.polygon_client.get_current_price(stock_data.symbol)
        company_details = self.polygon_client.get_company_details(stock_data.symbol)
        
        # Create stock holding
        stock_holding = StockHolding(
            symbol=stock_data.symbol,
            company_name=stock_data.company_name,
            shares=stock_data.shares,
            purchase_price=stock_data.purchase_price,
            purchase_date=stock_data.purchase_date,
            sector=stock_data.sector or (company_details.get('sector') if company_details else None),
            current_price=Decimal(str(current_price)) if current_price else None
        )
        
        # Calculate current values
        if stock_holding.current_price:
            stock_holding.market_value = stock_holding.current_price * stock_holding.shares
            stock_holding.gain_loss = stock_holding.market_value - (stock_holding.purchase_price * stock_holding.shares)
            if stock_holding.purchase_price > 0:
                stock_holding.gain_loss_percentage = (stock_holding.gain_loss / (stock_holding.purchase_price * stock_holding.shares)) * 100
        
        # Check if stock already exists in portfolio
        existing_stock_index = None
        for i, existing_stock in enumerate(portfolio.stocks):
            if existing_stock.symbol == stock_data.symbol:
                existing_stock_index = i
                break
        
        if existing_stock_index is not None:
            # Update existing holding (average cost)
            existing_stock = portfolio.stocks[existing_stock_index]
            total_shares = existing_stock.shares + stock_holding.shares
            total_cost = (existing_stock.shares * existing_stock.purchase_price) + (stock_holding.shares * stock_holding.purchase_price)
            avg_price = total_cost / total_shares
            
            # Update the existing stock
            existing_stock.shares = total_shares
            existing_stock.purchase_price = avg_price
            existing_stock.current_price = stock_holding.current_price
            existing_stock.market_value = existing_stock.current_price * existing_stock.shares if existing_stock.current_price else None
            if existing_stock.market_value:
                existing_stock.gain_loss = existing_stock.market_value - (existing_stock.purchase_price * existing_stock.shares)
                existing_stock.gain_loss_percentage = (existing_stock.gain_loss / (existing_stock.purchase_price * existing_stock.shares)) * 100
        else:
            # Add new stock
            portfolio.stocks.append(stock_holding)
        
        # Update portfolio totals
        await self._update_portfolio_values(portfolio)
        
        # Save to storage
        updates = {
            'stocks': [stock.dict() for stock in portfolio.stocks],
            'total_value': portfolio.total_value,
            'total_cost': portfolio.total_cost,
            'total_gain_loss': portfolio.total_gain_loss,
            'total_gain_loss_percentage': portfolio.total_gain_loss_percentage
        }
        
        return await self.storage.update_portfolio(user_id, portfolio_id, updates)
    
    async def update_stock_in_portfolio(self, user_id: str, portfolio_id: str, symbol: str, stock_update: StockHoldingUpdate) -> Optional[Portfolio]:
        """Update a stock holding in a portfolio."""
        portfolio = await self.storage.get_portfolio(user_id, portfolio_id)
        if not portfolio:
            return None
        
        # Find the stock
        stock_index = None
        for i, stock in enumerate(portfolio.stocks):
            if stock.symbol == symbol:
                stock_index = i
                break
        
        if stock_index is None:
            return None
        
        # Update stock data
        stock = portfolio.stocks[stock_index]
        if stock_update.shares:
            stock.shares = stock_update.shares
        if stock_update.purchase_price:
            stock.purchase_price = stock_update.purchase_price
        if stock_update.purchase_date:
            stock.purchase_date = stock_update.purchase_date
        if stock_update.sector:
            stock.sector = stock_update.sector
        
        # Update current price and calculations
        current_price = self.polygon_client.get_current_price(symbol)
        if current_price:
            stock.current_price = Decimal(str(current_price))
            stock.market_value = stock.current_price * stock.shares
            stock.gain_loss = stock.market_value - (stock.purchase_price * stock.shares)
            if stock.purchase_price > 0:
                stock.gain_loss_percentage = (stock.gain_loss / (stock.purchase_price * stock.shares)) * 100
        
        # Update portfolio totals
        await self._update_portfolio_values(portfolio)
        
        # Save to storage
        updates = {
            'stocks': [stock.dict() for stock in portfolio.stocks],
            'total_value': portfolio.total_value,
            'total_cost': portfolio.total_cost,
            'total_gain_loss': portfolio.total_gain_loss,
            'total_gain_loss_percentage': portfolio.total_gain_loss_percentage
        }
        
        return await self.storage.update_portfolio(user_id, portfolio_id, updates)
    
    async def remove_stock_from_portfolio(self, user_id: str, portfolio_id: str, symbol: str) -> Optional[Portfolio]:
        """Remove a stock from a portfolio."""
        portfolio = await self.storage.get_portfolio(user_id, portfolio_id)
        if not portfolio:
            return None
        
        # Remove the stock
        portfolio.stocks = [stock for stock in portfolio.stocks if stock.symbol != symbol]
        
        # Update portfolio totals
        await self._update_portfolio_values(portfolio)
        
        # Save to storage
        updates = {
            'stocks': [stock.dict() for stock in portfolio.stocks],
            'total_value': portfolio.total_value,
            'total_cost': portfolio.total_cost,
            'total_gain_loss': portfolio.total_gain_loss,
            'total_gain_loss_percentage': portfolio.total_gain_loss_percentage
        }
        
        return await self.storage.update_portfolio(user_id, portfolio_id, updates)
    
    async def get_portfolio_analytics(self, user_id: str, portfolio_id: str) -> Optional[PortfolioAnalytics]:
        """Get detailed analytics for a portfolio."""
        portfolio = await self.get_portfolio(user_id, portfolio_id)
        if not portfolio:
            return None
        
        # Calculate sector allocation
        sector_allocation = {}
        total_value = portfolio.total_value or Decimal('0')
        
        for stock in portfolio.stocks:
            sector = stock.sector or "Unknown"
            stock_value = stock.market_value or (stock.shares * stock.purchase_price)
            if sector not in sector_allocation:
                sector_allocation[sector] = Decimal('0')
            sector_allocation[sector] += stock_value
        
        # Convert to percentages
        if total_value > 0:
            for sector in sector_allocation:
                sector_allocation[sector] = (sector_allocation[sector] / total_value) * 100
        
        # Find top and worst performers
        stocks_with_performance = [stock for stock in portfolio.stocks if stock.gain_loss_percentage is not None]
        stocks_with_performance.sort(key=lambda x: x.gain_loss_percentage, reverse=True)
        
        top_performers = stocks_with_performance[:3]
        worst_performers = stocks_with_performance[-3:] if len(stocks_with_performance) > 3 else []
        
        # Calculate risk score (simple volatility-based metric)
        risk_score = self._calculate_portfolio_risk(portfolio)
        
        # Calculate diversification score
        diversification_score = self._calculate_diversification_score(portfolio)
        
        return PortfolioAnalytics(
            portfolio_id=portfolio_id,
            total_value=portfolio.total_value or Decimal('0'),
            total_cost=portfolio.total_cost or Decimal('0'),
            total_gain_loss=portfolio.total_gain_loss or Decimal('0'),
            total_gain_loss_percentage=portfolio.total_gain_loss_percentage or Decimal('0'),
            sector_allocation=sector_allocation,
            top_performers=top_performers,
            worst_performers=worst_performers,
            risk_score=risk_score,
            diversification_score=diversification_score
        )
    
    async def _update_portfolio_values(self, portfolio: Portfolio):
        """Update all portfolio values with current market data."""
        total_value = Decimal('0')
        total_cost = Decimal('0')
        
        for stock in portfolio.stocks:
            # Get current price
            current_price = self.polygon_client.get_current_price(stock.symbol)
            if current_price:
                stock.current_price = Decimal(str(current_price))
                stock.market_value = stock.current_price * stock.shares
            else:
                stock.market_value = stock.shares * stock.purchase_price
            
            # Calculate gain/loss
            cost_basis = stock.purchase_price * stock.shares
            stock.gain_loss = stock.market_value - cost_basis
            if cost_basis > 0:
                stock.gain_loss_percentage = (stock.gain_loss / cost_basis) * 100
            
            # Add to totals
            total_value += stock.market_value
            total_cost += cost_basis
        
        # Update portfolio totals
        portfolio.total_value = total_value
        portfolio.total_cost = total_cost
        portfolio.total_gain_loss = total_value - total_cost
        if total_cost > 0:
            portfolio.total_gain_loss_percentage = (portfolio.total_gain_loss / total_cost) * 100
    
    def _calculate_portfolio_risk(self, portfolio: Portfolio) -> Optional[Decimal]:
        """Calculate a simple risk score based on volatility and concentration."""
        if not portfolio.stocks:
            return None
        
        # Simple risk calculation based on:
        # 1. Number of stocks (diversification)
        # 2. Sector concentration
        # 3. Individual stock volatility (if available)
        
        num_stocks = len(portfolio.stocks)
        diversification_factor = min(1.0, num_stocks / 10.0)  # 10 stocks = good diversification
        
        # Sector concentration
        sectors = {}
        total_value = portfolio.total_value or Decimal('1')
        
        for stock in portfolio.stocks:
            sector = stock.sector or "Unknown"
            stock_value = stock.market_value or (stock.shares * stock.purchase_price)
            if sector not in sectors:
                sectors[sector] = Decimal('0')
            sectors[sector] += stock_value
        
        # Calculate Herfindahl index for concentration
        concentration_index = sum((value / total_value) ** 2 for value in sectors.values())
        
        # Risk score (0-100, higher = more risky)
        # Low diversification and high concentration = high risk
        risk_score = ((1 - diversification_factor) * 50) + (concentration_index * 50)
        
        return Decimal(str(round(risk_score, 2)))
    
    def _calculate_diversification_score(self, portfolio: Portfolio) -> Optional[Decimal]:
        """Calculate diversification score (0-100, higher = better diversified)."""
        if not portfolio.stocks:
            return None
        
        # Factors for diversification:
        # 1. Number of stocks
        # 2. Sector distribution
        # 3. Position size distribution
        
        num_stocks = len(portfolio.stocks)
        stock_score = min(100, (num_stocks / 20) * 50)  # 20 stocks = 50 points max
        
        # Sector distribution
        sectors = set(stock.sector for stock in portfolio.stocks if stock.sector)
        sector_score = min(50, len(sectors) * 5)  # 10 sectors = 50 points max
        
        return Decimal(str(round(stock_score + sector_score, 2)))