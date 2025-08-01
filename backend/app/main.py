from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, portfolio, analysis, health, chat
from app.utils.logger import setup_logger
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger()

# Create FastAPI app
app = FastAPI(
    title="Stock Portfolio Analysis API",
    description="A RAG-powered stock portfolio analysis system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(health.router, prefix="/api", tags=["Health"])

@app.on_event("startup")
async def startup_event():
    logger.info("Stock Portfolio Analysis API starting up...")
    # Initialize vector store, DynamoDB connections, etc.

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Stock Portfolio Analysis API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)