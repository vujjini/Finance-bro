from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from app.models.portfolio import (
    Portfolio, PortfolioCreate, PortfolioUpdate, PortfolioSummary, 
    StockHoldingCreate, StockHoldingUpdate, PortfolioAnalytics
)
from app.services.portfolio import PortfolioService
from app.routes.auth import get_current_user
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)
portfolio_service = PortfolioService()

@router.post("/", response_model=Portfolio)
async def create_portfolio(portfolio_data: PortfolioCreate, current_user = Depends(get_current_user)):
    """Create a new portfolio."""
    try:
        portfolio = await portfolio_service.create_portfolio(current_user.id, portfolio_data)
        logger.info(f"Portfolio created: {portfolio.id} for user {current_user.id}")
        return portfolio
        
    except Exception as e:
        logger.error(f"Error creating portfolio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portfolio"
        )

@router.get("/", response_model=List[PortfolioSummary])
async def get_user_portfolios(current_user = Depends(get_current_user)):
    """Get all portfolios for the current user."""
    try:
        portfolios = await portfolio_service.get_user_portfolios(current_user.id)
        return portfolios
        
    except Exception as e:
        logger.error(f"Error fetching portfolios: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch portfolios"
        )

@router.get("/{portfolio_id}", response_model=Portfolio)
async def get_portfolio(portfolio_id: str, current_user = Depends(get_current_user)):
    """Get a specific portfolio with updated values."""
    try:
        portfolio = await portfolio_service.get_portfolio(current_user.id, portfolio_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        return portfolio
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch portfolio"
        )

@router.put("/{portfolio_id}", response_model=Portfolio)
async def update_portfolio(
    portfolio_id: str, 
    portfolio_update: PortfolioUpdate, 
    current_user = Depends(get_current_user)
):
    """Update portfolio information."""
    try:
        portfolio = await portfolio_service.update_portfolio(current_user.id, portfolio_id, portfolio_update)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        logger.info(f"Portfolio updated: {portfolio_id}")
        return portfolio
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update portfolio"
        )

@router.delete("/{portfolio_id}")
async def delete_portfolio(portfolio_id: str, current_user = Depends(get_current_user)):
    """Delete a portfolio."""
    try:
        success = await portfolio_service.delete_portfolio(current_user.id, portfolio_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        logger.info(f"Portfolio deleted: {portfolio_id}")
        return {"message": "Portfolio deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete portfolio"
        )

@router.post("/{portfolio_id}/stocks", response_model=Portfolio)
async def add_stock_to_portfolio(
    portfolio_id: str, 
    stock_data: StockHoldingCreate, 
    current_user = Depends(get_current_user)
):
    """Add a stock to a portfolio."""
    try:
        portfolio = await portfolio_service.add_stock_to_portfolio(current_user.id, portfolio_id, stock_data)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        logger.info(f"Stock {stock_data.symbol} added to portfolio {portfolio_id}")
        return portfolio
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding stock to portfolio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add stock to portfolio"
        )

@router.put("/{portfolio_id}/stocks/{symbol}", response_model=Portfolio)
async def update_stock_in_portfolio(
    portfolio_id: str, 
    symbol: str, 
    stock_update: StockHoldingUpdate, 
    current_user = Depends(get_current_user)
):
    """Update a stock holding in a portfolio."""
    try:
        portfolio = await portfolio_service.update_stock_in_portfolio(
            current_user.id, portfolio_id, symbol, stock_update
        )
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio or stock not found"
            )
        
        logger.info(f"Stock {symbol} updated in portfolio {portfolio_id}")
        return portfolio
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating stock in portfolio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update stock in portfolio"
        )

@router.delete("/{portfolio_id}/stocks/{symbol}", response_model=Portfolio)
async def remove_stock_from_portfolio(
    portfolio_id: str, 
    symbol: str, 
    current_user = Depends(get_current_user)
):
    """Remove a stock from a portfolio."""
    try:
        portfolio = await portfolio_service.remove_stock_from_portfolio(current_user.id, portfolio_id, symbol)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        logger.info(f"Stock {symbol} removed from portfolio {portfolio_id}")
        return portfolio
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing stock from portfolio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove stock from portfolio"
        )

@router.get("/{portfolio_id}/analytics", response_model=PortfolioAnalytics)
async def get_portfolio_analytics(portfolio_id: str, current_user = Depends(get_current_user)):
    """Get detailed analytics for a portfolio."""
    try:
        analytics = await portfolio_service.get_portfolio_analytics(current_user.id, portfolio_id)
        if not analytics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        return analytics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch portfolio analytics"
        )