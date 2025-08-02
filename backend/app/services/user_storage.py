# backend/app/services/user_storage.py
from typing import Dict, Optional
import uuid
from datetime import datetime
from ..models.user import User, UserCreate
from .auth import AuthService

class InMemoryUserStorage:
    def __init__(self):
        self.users: Dict[str, dict] = {}
        self.users_by_email: Dict[str, str] = {}
    
    def create_user(self, user_data: UserCreate) -> User:
        # Check if user already exists
        if user_data.email in self.users_by_email:
            raise ValueError("User already exists")
        
        # Create user
        user_id = str(uuid.uuid4())
        hashed_password = AuthService.get_password_hash(user_data.password)
        
        user_dict = {
            "id": user_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": hashed_password,
            "created_at": datetime.utcnow(),
            "is_active": True
        }
        
        self.users[user_id] = user_dict
        self.users_by_email[user_data.email] = user_id
        
        return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})
    
    def get_user_by_email(self, email: str) -> Optional[dict]:
        user_id = self.users_by_email.get(email)
        if user_id:
            return self.users.get(user_id)
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        user_dict = self.users.get(user_id)
        if user_dict:
            return User(**{k: v for k, v in user_dict.items() if k != "hashed_password"})
        return None

# Global instance (will replace with DynamoDB later)
user_storage = InMemoryUserStorage()

print(user_storage.users)