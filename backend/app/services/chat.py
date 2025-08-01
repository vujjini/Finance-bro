from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from app.models.analysis import ChatSession, ChatMessage, ChatRequest, ChatResponse, NewsSource
from app.models.user import User
from app.models.portfolio import Portfolio
from app.utils.vector_store import get_vector_store
from app.utils.polygon_client import get_polygon_client
from app.utils.logger import setup_logger
from langchain.chat_models import init_chat_model
import json

logger = setup_logger(__name__)

class ChatService:
    def __init__(self):
        self.vector_store = get_vector_store()
        self.polygon_client = get_polygon_client()
        self.llm = init_chat_model("gemini-2.0-flash-001", model_provider="google_vertexai")
        self.sessions = {}  # In-memory storage (could be DynamoDB in production)
        
        logger.info("Chat service initialized")
    
    async def create_chat_session(self, user_id: str, portfolio_id: Optional[str] = None, stock_symbol: Optional[str] = None) -> ChatSession:
        """Create a new chat session."""
        session_id = str(uuid.uuid4())
        
        session = ChatSession(
            id=session_id,
            user_id=user_id,
            portfolio_id=portfolio_id,
            stock_symbol=stock_symbol,
            messages=[],
            context_documents=[],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created chat session {session_id} for user {user_id}")
        return session
    
    async def get_chat_session(self, session_id: str) -> Optional[ChatSession]:
        """Get an existing chat session."""
        return self.sessions.get(session_id)
    
    async def send_message(self, request: ChatRequest, user: User) -> ChatResponse:
        """Send a message and get AI response."""
        
        # Get or create session
        if request.session_id:
            session = await self.get_chat_session(request.session_id)
            if not session or session.user_id != user.id:
                raise ValueError("Invalid session ID")
        else:
            session = await self.create_chat_session(
                user.id, 
                request.portfolio_id, 
                request.stock_symbol
            )
        
        # Add user message to session
        user_message = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.utcnow()
        )
        session.messages.append(user_message)
        
        # Generate AI response
        ai_response_content, sources = await self._generate_ai_response(
            request.message, session, user
        )
        
        # Add AI response to session
        ai_message = ChatMessage(
            role="assistant",
            content=ai_response_content,
            timestamp=datetime.utcnow()
        )
        session.messages.append(ai_message)
        
        # Update session
        session.updated_at = datetime.utcnow()
        self.sessions[session.id] = session
        
        return ChatResponse(
            session_id=session.id,
            message=ai_message,
            sources=sources
        )
    
    async def get_chat_history(self, session_id: str, user_id: str) -> List[ChatMessage]:
        """Get chat history for a session."""
        session = await self.get_chat_session(session_id)
        if not session or session.user_id != user_id:
            return []
        
        return session.messages
    
    async def delete_chat_session(self, session_id: str, user_id: str) -> bool:
        """Delete a chat session."""
        session = await self.get_chat_session(session_id)
        if not session or session.user_id != user_id:
            return False
        
        del self.sessions[session_id]
        logger.info(f"Deleted chat session {session_id}")
        return True
    
    async def _generate_ai_response(self, user_message: str, session: ChatSession, user: User) -> tuple[str, List[NewsSource]]:
        """Generate AI response using RAG and conversation context."""
        
        # Determine context symbol
        context_symbol = session.stock_symbol
        if not context_symbol and session.portfolio_id:
            # If portfolio context, we might need to handle multiple stocks
            # For now, we'll use general portfolio context
            pass
        
        # Retrieve relevant documents
        relevant_docs = []
        sources = []
        
        if context_symbol:
            # Search for relevant documents about the specific stock
            relevant_docs = self.vector_store.search_documents(
                user_message, symbol=context_symbol, limit=5
            )
            
            # Convert to news sources for response
            for doc in relevant_docs:
                if doc.get('url') and doc.get('title'):
                    sources.append(NewsSource(
                        title=doc['title'],
                        url=doc['url'],
                        published_date=datetime.fromisoformat(doc.get('published_date', datetime.utcnow().isoformat())),
                        source=doc.get('source', 'Unknown'),
                        relevance_score=doc.get('score', 0.8)
                    ))
        else:
            # General search across all documents
            relevant_docs = self.vector_store.search_documents(user_message, limit=3)
        
        # Build context for the AI
        context = await self._build_chat_context(session, user, relevant_docs)
        
        # Create the prompt
        prompt = self._create_chat_prompt(user_message, context, session.messages[-6:])  # Last 6 messages for context
        
        try:
            # Get AI response
            response = self.llm.invoke(prompt)
            return response.content, sources
            
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again later.", []
    
    async def _build_chat_context(self, session: ChatSession, user: User, relevant_docs: List[Dict[str, Any]]) -> str:
        """Build context for chat AI response."""
        
        context_parts = []
        
        # Add session context
        if session.stock_symbol:
            context_parts.append(f"This conversation is about {session.stock_symbol} stock.")
            
            # Get recent market data
            try:
                current_price = self.polygon_client.get_current_price(session.stock_symbol)
                if current_price:
                    context_parts.append(f"Current price of {session.stock_symbol}: ${current_price}")
                
                recent_data = self.polygon_client.get_stock_data(session.stock_symbol, days=5)
                if recent_data:
                    latest = recent_data[-1]
                    context_parts.append(f"Latest trading data: Open: ${latest['open']}, High: ${latest['high']}, Low: ${latest['low']}, Close: ${latest['close']}")
            except Exception:
                pass
        
        elif session.portfolio_id:
            context_parts.append(f"This conversation is about the user's portfolio (ID: {session.portfolio_id}).")
        
        # Add user profile context
        if user.profile:
            context_parts.append(f"User profile: Risk tolerance: {user.profile.risk_tolerance}, Goal: {user.profile.primary_goal}")
        
        # Add relevant documents
        if relevant_docs:
            context_parts.append("Relevant information from recent news:")
            for doc in relevant_docs[:3]:  # Top 3 most relevant
                context_parts.append(f"- {doc.get('title', 'News')}: {doc.get('content', '')[:200]}...")
        
        return "\n".join(context_parts)
    
    def _create_chat_prompt(self, user_message: str, context: str, recent_messages: List[ChatMessage]) -> str:
        """Create prompt for chat AI."""
        
        # Build conversation history
        conversation_history = ""
        for msg in recent_messages[:-1]:  # Exclude the current message
            conversation_history += f"{msg.role.title()}: {msg.content}\n"
        
        prompt = f"""
        You are a helpful financial advisor AI assistant. You're having a conversation with a user about their investments and portfolio.

        Context:
        {context}

        Recent conversation:
        {conversation_history}

        User's current message: {user_message}

        Instructions:
        1. Provide helpful, accurate financial information based on the context provided
        2. If discussing specific stocks, reference the relevant news and data from the context
        3. Be conversational and maintain the flow of the ongoing discussion
        4. If you don't have enough information to answer accurately, say so
        5. Always include appropriate disclaimers about investment advice
        6. Keep responses concise but informative (2-3 paragraphs max)
        7. If the user asks about something not covered in the context, acknowledge the limitation

        Respond as a knowledgeable but cautious financial advisor assistant.
        """
        
        return prompt
    
    async def get_user_chat_sessions(self, user_id: str) -> List[ChatSession]:
        """Get all chat sessions for a user."""
        user_sessions = []
        
        for session in self.sessions.values():
            if session.user_id == user_id:
                user_sessions.append(session)
        
        # Sort by most recent
        user_sessions.sort(key=lambda x: x.updated_at, reverse=True)
        return user_sessions
    
    def _clean_old_sessions(self):
        """Clean up old chat sessions (call periodically)."""
        cutoff_date = datetime.utcnow() - timedelta(days=7)  # Keep sessions for 7 days
        
        sessions_to_delete = []
        for session_id, session in self.sessions.items():
            if session.updated_at < cutoff_date:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            del self.sessions[session_id]
        
        if sessions_to_delete:
            logger.info(f"Cleaned up {len(sessions_to_delete)} old chat sessions")