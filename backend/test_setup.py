#!/usr/bin/env python3
"""
Test script to verify the backend setup and dependencies.
Run this script to check if all components are working correctly.
"""

import sys
import os
from dotenv import load_dotenv

def test_imports():
    """Test if all required packages can be imported."""
    print("Testing imports...")
    
    try:
        import fastapi
        print("✓ FastAPI imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import FastAPI: {e}")
        return False
    
    try:
        import uvicorn
        print("✓ Uvicorn imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Uvicorn: {e}")
        return False
    
    try:
        from langchain.chat_models import init_chat_model
        print("✓ LangChain imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import LangChain: {e}")
        return False
    
    try:
        from qdrant_client import QdrantClient
        print("✓ Qdrant client imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Qdrant: {e}")
        return False
    
    try:
        import boto3
        print("✓ Boto3 imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Boto3: {e}")
        return False
    
    try:
        from polygon import RESTClient
        print("✓ Polygon client imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Polygon client: {e}")
        return False
    
    return True

def test_environment():
    """Test environment variables."""
    print("\nTesting environment variables...")
    
    load_dotenv()
    
    required_vars = [
        "JWT_SECRET_KEY",
        "POLYGON_API_KEY", 
        "GOOGLE_APPLICATION_CREDENTIALS"
    ]
    
    all_present = True
    for var in required_vars:
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"✗ {var} is not set")
            all_present = False
    
    return all_present

def test_app_structure():
    """Test application structure."""
    print("\nTesting application structure...")
    
    required_files = [
        "app/__init__.py",
        "app/main.py",
        "app/models/__init__.py",
        "app/routes/__init__.py", 
        "app/services/__init__.py",
        "app/utils/__init__.py"
    ]
    
    all_present = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            all_present = False
    
    return all_present

def test_app_import():
    """Test if the FastAPI app can be imported."""
    print("\nTesting FastAPI app import...")
    
    try:
        from app.main import app
        print("✓ FastAPI app imported successfully")
        print(f"✓ App title: {app.title}")
        return True
    except Exception as e:
        print(f"✗ Failed to import FastAPI app: {e}")
        return False

def test_services():
    """Test if services can be instantiated."""
    print("\nTesting services...")
    
    try:
        from app.services.auth import AuthService
        auth_service = AuthService()
        print("✓ Auth service created successfully")
    except Exception as e:
        print(f"✗ Failed to create auth service: {e}")
        return False
    
    try:
        from app.utils.logger import setup_logger
        logger = setup_logger()
        print("✓ Logger service created successfully")
    except Exception as e:
        print(f"✗ Failed to create logger: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("🚀 Stock Portfolio Analysis API - Setup Test\n")
    
    tests = [
        ("Package Imports", test_imports),
        ("Environment Variables", test_environment),
        ("Application Structure", test_app_structure),
        ("FastAPI App", test_app_import),
        ("Services", test_services)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name} test...")
        print('='*50)
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    all_passed = True
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 All tests passed! Your backend setup is ready.")
        print("\nTo start the server, run:")
        print("uvicorn app.main:app --reload")
        print("\nAPI will be available at: http://localhost:8000")
        print("API docs at: http://localhost:8000/docs")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nCommon solutions:")
        print("1. Install missing packages: pip install -r requirements.txt")
        print("2. Set up environment variables: cp .env.example .env")
        print("3. Check file structure and imports")
    print('='*50)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())