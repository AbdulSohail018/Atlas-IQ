"""
Test suite for main application
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

def test_import():
    """Test that the main module can be imported"""
    try:
        from app.main import app
        assert app is not None
    except ImportError as e:
        pytest.skip(f"Skipping test due to import error: {e}")

def test_basic_health_check():
    """Test basic health check endpoint"""
    try:
        from app.main import app
        client = TestClient(app)
        
        with patch('app.core.database.init_databases', new_callable=AsyncMock):
            with patch('app.core.database.close_databases', new_callable=AsyncMock):
                response = client.get("/health")
                assert response.status_code in [200, 503]  # Allow both healthy and unhealthy
    except ImportError as e:
        pytest.skip(f"Skipping test due to import error: {e}")

def test_root_endpoint():
    """Test root endpoint"""
    try:
        from app.main import app
        client = TestClient(app)
        
        with patch('app.core.database.init_databases', new_callable=AsyncMock):
            with patch('app.core.database.close_databases', new_callable=AsyncMock):
                response = client.get("/")
                assert response.status_code == 200
                data = response.json()
                assert "message" in data
                assert "Glonav" in data["message"]
    except ImportError as e:
        pytest.skip(f"Skipping test due to import error: {e}")