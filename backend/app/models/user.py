from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class RiskTolerance(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class InvestmentHorizon(str, Enum):
    SHORT_TERM = "short_term"  # < 1 year
    MEDIUM_TERM = "medium_term"  # 1-5 years
    LONG_TERM = "long_term"  # > 5 years

class InvestmentGoal(str, Enum):
    GROWTH = "growth"
    INCOME = "income"
    PRESERVATION = "preservation"
    LEARNING = "learning"

class LiquidityPreference(str, Enum):
    HIGH = "high"  # Need quick access to funds
    MEDIUM = "medium"
    LOW = "low"  # Comfortable with lock-ins

class UserProfile(BaseModel):
    risk_tolerance: RiskTolerance
    investment_horizon: Optional[InvestmentHorizon] = None
    primary_goal: InvestmentGoal
    liquidity_preference: LiquidityPreference
    additional_info: Optional[str] = None

class User(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    profile: Optional[UserProfile] = None
    created_at: datetime
    updated_at: datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    profile: Optional[UserProfile] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    profile: Optional[UserProfile] = None

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    profile: Optional[UserProfile] = None
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    email: Optional[str] = None