from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.models.user import UserCreate, UserLogin, UserUpdate, UserResponse, Token
from app.services.auth import AuthService
from app.services.user_storage import UserStorageService
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)
security = HTTPBearer()
auth_service = AuthService()
user_storage = UserStorageService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user."""
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    
    if not token_data or not token_data.email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await user_storage.get_user_by_email(token_data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

@router.post("/register", response_model=dict)
async def register_user(user_data: UserCreate):
    """Register a new user."""
    try:
        # Validate user data
        auth_service.validate_user_registration(user_data)
        
        # Check if user already exists
        existing_user = await user_storage.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = auth_service.hash_password(user_data.password)
        
        # Generate user ID
        user_id = auth_service.generate_user_id()
        
        # Create user
        user = await user_storage.create_user(user_data, user_id, hashed_password)
        
        # Create token
        token = auth_service.create_token_response(user.email)
        
        logger.info(f"User registered successfully: {user.email}")
        
        return {
            "message": "User created successfully",
            "user": UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                profile=user.profile,
                created_at=user.created_at
            ),
            "token": token
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/login", response_model=dict)
async def login_user(credentials: UserLogin):
    """Authenticate user and return token."""
    try:
        # Get user by email
        user = await user_storage.get_user_by_email(credentials.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not auth_service.verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create token
        token = auth_service.create_token_response(user.email)
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return {
            "message": "Login successful",
            "user": UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                profile=user.profile,
                created_at=user.created_at
            ),
            "token": token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        profile=current_user.profile,
        created_at=current_user.created_at
    )

@router.put("/me", response_model=UserResponse)
async def update_user_profile(user_update: UserUpdate, current_user = Depends(get_current_user)):
    """Update current user profile."""
    try:
        updated_user = await user_storage.update_user(current_user.email, user_update)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        logger.info(f"User profile updated: {current_user.email}")
        
        return UserResponse(
            id=updated_user.id,
            email=updated_user.email,
            full_name=updated_user.full_name,
            profile=updated_user.profile,
            created_at=updated_user.created_at
        )
        
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user = Depends(get_current_user)):
    """Refresh access token."""
    try:
        token = auth_service.create_token_response(current_user.email)
        logger.info(f"Token refreshed for user: {current_user.email}")
        return token
        
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/me")
async def delete_user_account(current_user = Depends(get_current_user)):
    """Delete current user account."""
    try:
        success = await user_storage.delete_user(current_user.email)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        logger.info(f"User account deleted: {current_user.email}")
        return {"message": "Account deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting user account: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )