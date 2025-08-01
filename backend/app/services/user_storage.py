import boto3
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import json
from decimal import Decimal
from app.models.user import User, UserCreate, UserUpdate, UserResponse
from app.models.portfolio import Portfolio, PortfolioCreate, StockHolding
from app.utils.logger import setup_logger
from botocore.exceptions import ClientError

logger = setup_logger(__name__)

class DynamoDBManager:
    def __init__(self):
        # Configure AWS credentials and region
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        # For local development, use DynamoDB Local or mock
        use_local = os.getenv("USE_LOCAL_DYNAMODB", "false").lower() == "true"
        
        if use_local:
            self.dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url='http://localhost:8000',
                region_name=self.region,
                aws_access_key_id='fake',
                aws_secret_access_key='fake'
            )
        else:
            self.dynamodb = boto3.resource('dynamodb', region_name=self.region)
        
        self.users_table_name = os.getenv("USERS_TABLE", "StockAnalysis-Users")
        self.portfolios_table_name = os.getenv("PORTFOLIOS_TABLE", "StockAnalysis-Portfolios")
        
        # Initialize tables
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Create tables if they don't exist (for local development)."""
        try:
            # Users table
            try:
                self.users_table = self.dynamodb.Table(self.users_table_name)
                self.users_table.load()
            except ClientError:
                logger.info(f"Creating users table: {self.users_table_name}")
                self.users_table = self._create_users_table()
            
            # Portfolios table
            try:
                self.portfolios_table = self.dynamodb.Table(self.portfolios_table_name)
                self.portfolios_table.load()
            except ClientError:
                logger.info(f"Creating portfolios table: {self.portfolios_table_name}")
                self.portfolios_table = self._create_portfolios_table()
                
        except Exception as e:
            logger.error(f"Error setting up DynamoDB tables: {str(e)}")
            # Fallback to in-memory storage for development
            self._use_memory_fallback()
    
    def _create_users_table(self):
        """Create the users table."""
        return self.dynamodb.create_table(
            TableName=self.users_table_name,
            KeySchema=[
                {'AttributeName': 'email', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'email', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    
    def _create_portfolios_table(self):
        """Create the portfolios table."""
        return self.dynamodb.create_table(
            TableName=self.portfolios_table_name,
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'portfolio_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'portfolio_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    
    def _use_memory_fallback(self):
        """Fallback to in-memory storage for development."""
        logger.warning("Using in-memory storage fallback")
        self._users_memory = {}
        self._portfolios_memory = {}
        self.use_memory = True
    
    def _to_dynamodb_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Python dict to DynamoDB format."""
        if isinstance(data, dict):
            return {k: self._to_dynamodb_item(v) for k, v in data.items() if v is not None}
        elif isinstance(data, list):
            return [self._to_dynamodb_item(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, Decimal):
            return float(data)
        else:
            return data
    
    def _from_dynamodb_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DynamoDB item to Python dict."""
        if isinstance(item, dict):
            result = {}
            for k, v in item.items():
                if isinstance(v, str) and self._is_iso_datetime(v):
                    result[k] = datetime.fromisoformat(v)
                else:
                    result[k] = self._from_dynamodb_item(v)
            return result
        elif isinstance(item, list):
            return [self._from_dynamodb_item(i) for i in item]
        else:
            return item
    
    def _is_iso_datetime(self, value: str) -> bool:
        """Check if string is ISO datetime format."""
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
            return True
        except:
            return False

class UserStorageService(DynamoDBManager):
    def __init__(self):
        super().__init__()
    
    async def create_user(self, user_data: UserCreate, user_id: str, hashed_password: str) -> User:
        """Create a new user."""
        now = datetime.utcnow()
        
        user_item = {
            'id': user_id,
            'email': user_data.email,
            'full_name': user_data.full_name,
            'password_hash': hashed_password,
            'profile': user_data.profile.dict() if user_data.profile else None,
            'created_at': now,
            'updated_at': now
        }
        
        try:
            if hasattr(self, 'use_memory'):
                self._users_memory[user_data.email] = user_item
            else:
                self.users_table.put_item(
                    Item=self._to_dynamodb_item(user_item),
                    ConditionExpression='attribute_not_exists(email)'
                )
            
            return User(**user_item)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise ValueError("User with this email already exists")
            raise e
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            if hasattr(self, 'use_memory'):
                user_data = self._users_memory.get(email)
                if user_data:
                    return User(**user_data)
                return None
            
            response = self.users_table.get_item(Key={'email': email})
            if 'Item' in response:
                user_data = self._from_dynamodb_item(response['Item'])
                return User(**user_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            return None
    
    async def update_user(self, email: str, user_update: UserUpdate) -> Optional[User]:
        """Update user information."""
        now = datetime.utcnow()
        
        try:
            if hasattr(self, 'use_memory'):
                if email in self._users_memory:
                    user_data = self._users_memory[email]
                    if user_update.full_name:
                        user_data['full_name'] = user_update.full_name
                    if user_update.profile:
                        user_data['profile'] = user_update.profile.dict()
                    user_data['updated_at'] = now
                    return User(**user_data)
                return None
            
            # Build update expression
            update_expression = "SET updated_at = :updated_at"
            expression_values = {':updated_at': now.isoformat()}
            
            if user_update.full_name:
                update_expression += ", full_name = :full_name"
                expression_values[':full_name'] = user_update.full_name
            
            if user_update.profile:
                update_expression += ", profile = :profile"
                expression_values[':profile'] = user_update.profile.dict()
            
            response = self.users_table.update_item(
                Key={'email': email},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            
            if 'Attributes' in response:
                user_data = self._from_dynamodb_item(response['Attributes'])
                return User(**user_data)
            return None
            
        except Exception as e:
            logger.error(f"Error updating user {email}: {str(e)}")
            return None
    
    async def delete_user(self, email: str) -> bool:
        """Delete a user."""
        try:
            if hasattr(self, 'use_memory'):
                if email in self._users_memory:
                    del self._users_memory[email]
                    return True
                return False
            
            self.users_table.delete_item(Key={'email': email})
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {email}: {str(e)}")
            return False

class PortfolioStorageService(DynamoDBManager):
    def __init__(self):
        super().__init__()
    
    async def create_portfolio(self, user_id: str, portfolio_id: str, portfolio_data: PortfolioCreate) -> Portfolio:
        """Create a new portfolio."""
        now = datetime.utcnow()
        
        portfolio_item = {
            'id': portfolio_id,
            'user_id': user_id,
            'name': portfolio_data.name,
            'description': portfolio_data.description,
            'stocks': [],
            'total_value': None,
            'total_cost': None,
            'total_gain_loss': None,
            'total_gain_loss_percentage': None,
            'created_at': now,
            'updated_at': now
        }
        
        try:
            if hasattr(self, 'use_memory'):
                portfolio_key = f"{user_id}#{portfolio_id}"
                self._portfolios_memory[portfolio_key] = portfolio_item
            else:
                self.portfolios_table.put_item(
                    Item=self._to_dynamodb_item(portfolio_item)
                )
            
            return Portfolio(**portfolio_item)
            
        except Exception as e:
            logger.error(f"Error creating portfolio: {str(e)}")
            raise e
    
    async def get_user_portfolios(self, user_id: str) -> List[Portfolio]:
        """Get all portfolios for a user."""
        try:
            if hasattr(self, 'use_memory'):
                portfolios = []
                for key, portfolio_data in self._portfolios_memory.items():
                    if key.startswith(f"{user_id}#"):
                        portfolios.append(Portfolio(**portfolio_data))
                return portfolios
            
            response = self.portfolios_table.query(
                KeyConditionExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )
            
            portfolios = []
            for item in response.get('Items', []):
                portfolio_data = self._from_dynamodb_item(item)
                portfolios.append(Portfolio(**portfolio_data))
            
            return portfolios
            
        except Exception as e:
            logger.error(f"Error getting portfolios for user {user_id}: {str(e)}")
            return []
    
    async def get_portfolio(self, user_id: str, portfolio_id: str) -> Optional[Portfolio]:
        """Get a specific portfolio."""
        try:
            if hasattr(self, 'use_memory'):
                portfolio_key = f"{user_id}#{portfolio_id}"
                portfolio_data = self._portfolios_memory.get(portfolio_key)
                if portfolio_data:
                    return Portfolio(**portfolio_data)
                return None
            
            response = self.portfolios_table.get_item(
                Key={'user_id': user_id, 'portfolio_id': portfolio_id}
            )
            
            if 'Item' in response:
                portfolio_data = self._from_dynamodb_item(response['Item'])
                return Portfolio(**portfolio_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting portfolio {portfolio_id}: {str(e)}")
            return None
    
    async def update_portfolio(self, user_id: str, portfolio_id: str, updates: Dict[str, Any]) -> Optional[Portfolio]:
        """Update portfolio data."""
        now = datetime.utcnow()
        updates['updated_at'] = now
        
        try:
            if hasattr(self, 'use_memory'):
                portfolio_key = f"{user_id}#{portfolio_id}"
                if portfolio_key in self._portfolios_memory:
                    self._portfolios_memory[portfolio_key].update(updates)
                    return Portfolio(**self._portfolios_memory[portfolio_key])
                return None
            
            # Build update expression
            update_expression = "SET "
            expression_values = {}
            
            for key, value in updates.items():
                update_expression += f"{key} = :{key}, "
                expression_values[f":{key}"] = value
            
            update_expression = update_expression.rstrip(', ')
            
            response = self.portfolios_table.update_item(
                Key={'user_id': user_id, 'portfolio_id': portfolio_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=self._to_dynamodb_item(expression_values),
                ReturnValues='ALL_NEW'
            )
            
            if 'Attributes' in response:
                portfolio_data = self._from_dynamodb_item(response['Attributes'])
                return Portfolio(**portfolio_data)
            return None
            
        except Exception as e:
            logger.error(f"Error updating portfolio {portfolio_id}: {str(e)}")
            return None
    
    async def delete_portfolio(self, user_id: str, portfolio_id: str) -> bool:
        """Delete a portfolio."""
        try:
            if hasattr(self, 'use_memory'):
                portfolio_key = f"{user_id}#{portfolio_id}"
                if portfolio_key in self._portfolios_memory:
                    del self._portfolios_memory[portfolio_key]
                    return True
                return False
            
            self.portfolios_table.delete_item(
                Key={'user_id': user_id, 'portfolio_id': portfolio_id}
            )
            return True
            
        except Exception as e:
            logger.error(f"Error deleting portfolio {portfolio_id}: {str(e)}")
            return False