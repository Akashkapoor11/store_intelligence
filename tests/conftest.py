"""
conftest.py — pytest fixtures for integration tests
"""
import pytest
import requests

API_BASE = "http://localhost:8000"

@pytest.fixture(scope="session")
def api_base():
    return API_BASE

@pytest.fixture(scope="session")
def health(api_base):
    try:
        return requests.get(f"{api_base}/health", timeout=5).json()
    except Exception:
        return {}
