# backend/app/routes/auth.py
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import timedelta

from ..models.user import User, UserCreate, UserLogin, Token
from ..services.auth import AuthService
from ..services.user_storage import user_storage
import os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=User)
async def register(user_data: UserCreate):
    try:
        user = user_storage.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    # Authenticate user
    user_dict = user_storage.get_user_by_email(user_data.email)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email is not registered"
        )
    if not user_dict or not AuthService.verify_password(user_data.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")))
    access_token = AuthService.create_access_token(
        data={"sub": user_dict["email"]}, 
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token_data = AuthService.verify_token(credentials.credentials)
    user_dict = user_storage.get_user_by_email(token_data["email"])
    
    if user_dict is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user