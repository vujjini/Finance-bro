from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from app.models.analysis import ChatSession, ChatMessage, ChatRequest, ChatResponse
from app.services.chat import ChatService
from app.routes.auth import get_current_user
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)
chat_service = ChatService()

@router.post("/", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user = Depends(get_current_user)
):
    """Send a message to the AI assistant."""
    try:
        response = await chat_service.send_message(request, current_user)
        logger.info(f"Chat message processed for user {current_user.id}")
        return response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )

@router.post("/session", response_model=ChatSession)
async def create_chat_session(
    portfolio_id: str = None,
    stock_symbol: str = None,
    current_user = Depends(get_current_user)
):
    """Create a new chat session."""
    try:
        session = await chat_service.create_chat_session(
            current_user.id, 
            portfolio_id, 
            stock_symbol
        )
        logger.info(f"Chat session created: {session.id} for user {current_user.id}")
        return session
        
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session"
        )

@router.get("/sessions", response_model=List[ChatSession])
async def get_user_chat_sessions(current_user = Depends(get_current_user)):
    """Get all chat sessions for the current user."""
    try:
        sessions = await chat_service.get_user_chat_sessions(current_user.id)
        return sessions
        
    except Exception as e:
        logger.error(f"Error fetching chat sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat sessions"
        )

@router.get("/session/{session_id}", response_model=ChatSession)
async def get_chat_session(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific chat session."""
    try:
        session = await chat_service.get_chat_session(session_id)
        if not session or session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat session"
        )

@router.get("/session/{session_id}/history", response_model=List[ChatMessage])
async def get_chat_history(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Get chat history for a session."""
    try:
        messages = await chat_service.get_chat_history(session_id, current_user.id)
        return messages
        
    except Exception as e:
        logger.error(f"Error fetching chat history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch chat history"
        )

@router.delete("/session/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a chat session."""
    try:
        success = await chat_service.delete_chat_session(session_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        logger.info(f"Chat session deleted: {session_id}")
        return {"message": "Chat session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat session"
        )