from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from app.models.analysis import (
    StockAnalysis, PortfolioAnalysis, PortfolioAnalysisRequest, 
    MarketRecommendation
)
from app.services.analysis import AnalysisService
from app.services.portfolio import PortfolioService
from app.routes.auth import get_current_user
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)
analysis_service = AnalysisService()
portfolio_service = PortfolioService()

@router.post("/stock/{symbol}", response_model=StockAnalysis)
async def analyze_stock(
    symbol: str, 
    company_name: str = Query(..., description="Company name for the stock"),
    portfolio_id: Optional[str] = Query(None, description="Portfolio ID for context"),
    current_user = Depends(get_current_user)
):
    """Analyze a specific stock using RAG."""
    try:
        # Get portfolio context if provided
        portfolio = None
        if portfolio_id:
            portfolio = await portfolio_service.get_portfolio(current_user.id, portfolio_id)
            if not portfolio:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Portfolio not found"
                )
        
        # Perform analysis
        analysis = await analysis_service.analyze_stock(
            symbol.upper(), 
            company_name, 
            current_user, 
            portfolio
        )
        
        logger.info(f"Stock analysis completed for {symbol} by user {current_user.id}")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing stock {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze stock"
        )

@router.post("/portfolio/{portfolio_id}", response_model=PortfolioAnalysis)
async def analyze_portfolio(
    portfolio_id: str,
    include_recommendations: bool = Query(True, description="Include market recommendations"),
    current_user = Depends(get_current_user)
):
    """Analyze an entire portfolio using RAG."""
    try:
        # Get portfolio
        portfolio = await portfolio_service.get_portfolio(current_user.id, portfolio_id)
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        # Create analysis request
        request = PortfolioAnalysisRequest(
            portfolio_id=portfolio_id,
            include_recommendations=include_recommendations
        )
        
        # Perform analysis
        analysis = await analysis_service.analyze_portfolio(request, current_user, portfolio)
        
        logger.info(f"Portfolio analysis completed for {portfolio_id} by user {current_user.id}")
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze portfolio"
        )

@router.get("/recommendations", response_model=List[MarketRecommendation])
async def get_market_recommendations(
    recommendation_type: str = Query("stocks", description="Type of recommendations (stocks, forex, crypto)"),
    limit: int = Query(5, ge=1, le=20, description="Number of recommendations"),
    current_user = Depends(get_current_user)
):
    """Get market recommendations for different asset types."""
    try:
        recommendations = await analysis_service.get_market_recommendations(
            recommendation_type=recommendation_type,
            limit=limit
        )
        
        logger.info(f"Market recommendations generated for user {current_user.id}")
        return recommendations
        
    except Exception as e:
        logger.error(f"Error generating market recommendations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate market recommendations"
        )

@router.get("/stock/{symbol}/quick", response_model=dict)
async def get_quick_stock_info(
    symbol: str,
    current_user = Depends(get_current_user)
):
    """Get quick information about a stock without full analysis."""
    try:
        from app.utils.polygon_client import get_polygon_client
        
        polygon_client = get_polygon_client()
        
        # Get basic info
        current_price = polygon_client.get_current_price(symbol.upper())
        company_details = polygon_client.get_company_details(symbol.upper())
        recent_data = polygon_client.get_stock_data(symbol.upper(), days=5)
        
        if not current_price or not company_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock information not found"
            )
        
        # Calculate basic metrics
        price_change = 0
        price_change_percent = 0
        
        if recent_data and len(recent_data) >= 2:
            yesterday_close = recent_data[-2]['close']
            today_close = recent_data[-1]['close']
            price_change = today_close - yesterday_close
            price_change_percent = (price_change / yesterday_close) * 100
        
        quick_info = {
            "symbol": symbol.upper(),
            "company_name": company_details['name'],
            "current_price": current_price,
            "price_change": price_change,
            "price_change_percent": round(price_change_percent, 2),
            "sector": company_details.get('sector', 'Unknown'),
            "market_cap": company_details.get('market_cap'),
            "website": company_details.get('website', ''),
            "last_updated": recent_data[-1]['date'] if recent_data else None
        }
        
        return quick_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quick stock info for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stock information"
        )

@router.get("/search/{query}", response_model=List[dict])
async def search_stocks(
    query: str,
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    current_user = Depends(get_current_user)
):
    """Search for stocks by symbol or company name."""
    try:
        from app.utils.polygon_client import get_polygon_client
        
        polygon_client = get_polygon_client()
        results = polygon_client.search_symbols(query, limit=limit)
        
        return results
        
    except Exception as e:
        logger.error(f"Error searching stocks for query '{query}': {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search stocks"
        )