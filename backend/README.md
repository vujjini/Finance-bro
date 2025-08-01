# Stock Portfolio Analysis API

A comprehensive FastAPI backend for stock portfolio analysis powered by RAG (Retrieval-Augmented Generation) technology. This API provides intelligent stock analysis, portfolio management, and AI-powered chat functionality for investment insights.

## Features

- **RAG-Powered Analysis**: Comprehensive stock analysis using real-time news data and market information
- **Portfolio Management**: Full CRUD operations for portfolio and stock holdings
- **AI Chat Assistant**: Follow-up questions and interactive discussions about your investments
- **Real-time Market Data**: Integration with Polygon.io for current stock prices and historical data
- **User Authentication**: JWT-based authentication with secure user management
- **Scalable Architecture**: Built for AWS deployment with DynamoDB integration
- **Caching System**: Intelligent caching for improved performance
- **Comprehensive API**: RESTful API with automatic documentation

## Technology Stack

- **Framework**: FastAPI
- **Authentication**: JWT with passlib
- **Database**: DynamoDB (AWS)
- **Vector Database**: Qdrant
- **LLM**: Google Vertex AI (Gemini)
- **Market Data**: Polygon.io API
- **News Scraping**: Beautiful Soup + Requests
- **Deployment**: Docker + AWS

## Quick Start

### Prerequisites

1. Python 3.11+
2. Polygon.io API key
3. Google Cloud Service Account (for Vertex AI)
4. AWS credentials (for DynamoDB)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `JWT_SECRET_KEY` | Secret key for JWT tokens | Yes |
| `POLYGON_API_KEY` | Polygon.io API key | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Google Cloud service account JSON | Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Yes |
| `AWS_REGION` | AWS region | No (default: us-east-1) |
| `QDRANT_URL` | Qdrant vector database URL | No (default: :memory:) |
| `USE_LOCAL_DYNAMODB` | Use local DynamoDB for development | No (default: false) |

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user info
- `PUT /api/auth/me` - Update user profile
- `POST /api/auth/refresh` - Refresh access token

### Portfolio Management
- `GET /api/portfolio/` - Get user portfolios
- `POST /api/portfolio/` - Create new portfolio
- `GET /api/portfolio/{id}` - Get specific portfolio
- `PUT /api/portfolio/{id}` - Update portfolio
- `DELETE /api/portfolio/{id}` - Delete portfolio
- `POST /api/portfolio/{id}/stocks` - Add stock to portfolio
- `PUT /api/portfolio/{id}/stocks/{symbol}` - Update stock holding
- `DELETE /api/portfolio/{id}/stocks/{symbol}` - Remove stock
- `GET /api/portfolio/{id}/analytics` - Get portfolio analytics

### Analysis
- `POST /api/analysis/stock/{symbol}` - Analyze specific stock
- `POST /api/analysis/portfolio/{id}` - Analyze entire portfolio
- `GET /api/analysis/recommendations` - Get market recommendations
- `GET /api/analysis/stock/{symbol}/quick` - Get quick stock info
- `GET /api/analysis/search/{query}` - Search stocks

### Chat
- `POST /api/chat/` - Send message to AI assistant
- `POST /api/chat/session` - Create new chat session
- `GET /api/chat/sessions` - Get user chat sessions
- `GET /api/chat/session/{id}` - Get specific chat session
- `DELETE /api/chat/session/{id}` - Delete chat session

### Health
- `GET /api/health` - Basic health check
- `GET /api/health/detailed` - Detailed health with dependencies
- `GET /api/ready` - Kubernetes readiness probe
- `GET /api/live` - Kubernetes liveness probe

## API Documentation

Once the server is running, you can access:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Architecture

### Directory Structure
```
backend/
├── app/
│   ├── models/           # Pydantic models
│   ├── routes/           # FastAPI routers
│   ├── services/         # Business logic
│   ├── utils/            # Utilities
│   └── main.py          # Application entry point
├── tests/               # Test files
├── requirements.txt     # Dependencies
├── Dockerfile          # Container configuration
└── README.md           # This file
```

### Core Components

1. **Models**: Pydantic models for data validation and serialization
2. **Services**: Business logic layer with RAG analysis, portfolio management, and chat
3. **Routes**: FastAPI routers handling HTTP requests
4. **Utils**: Utilities for vector store, market data, and logging

### Data Flow

1. **User Request** → Routes → Services → External APIs/Database
2. **RAG Analysis**: News Scraping → Vector Store → LLM → Structured Response
3. **Portfolio Analysis**: Portfolio Data + Market Data + RAG Analysis → Comprehensive Report

## Development

### Running Tests
```bash
pytest
```

### Code Quality
```bash
# Format code
black app/

# Type checking
mypy app/

# Linting
flake8 app/
```

### Local Development with Docker
```bash
docker build -t stock-analysis-api .
docker run -p 8000:8000 --env-file .env stock-analysis-api
```

## Deployment

### AWS Deployment

1. **Build and push Docker image**
   ```bash
   docker build -t stock-analysis-api .
   docker tag stock-analysis-api:latest <aws-account>.dkr.ecr.<region>.amazonaws.com/stock-analysis-api:latest
   docker push <aws-account>.dkr.ecr.<region>.amazonaws.com/stock-analysis-api:latest
   ```

2. **Deploy using AWS ECS, Lambda, or EC2**

3. **Set up DynamoDB tables** (done automatically by the application)

4. **Configure environment variables** in your deployment environment

### Free Tier Considerations

- Use AWS Free Tier for DynamoDB
- Use Google Cloud Free Tier for Vertex AI
- Deploy on AWS Lambda for cost-effective serverless deployment
- Use Qdrant Cloud free tier for vector database

## Performance Optimization

- **Caching**: In-memory caching for analysis results (1-hour TTL)
- **Batch Processing**: Efficient portfolio analysis with parallel stock analysis
- **Connection Pooling**: Optimized database connections
- **Rate Limiting**: Built-in rate limiting for external API calls

## Security

- JWT-based authentication
- Password hashing with bcrypt
- Input validation with Pydantic
- CORS configuration
- Environment variable protection
- Non-root Docker user

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the health check endpoints
3. Check logs for detailed error information
4. Create an issue in the repository