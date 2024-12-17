import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import app
from dependencies import get_db

@pytest.fixture
def db():
    session=get_db()
    return session

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def auth_client(client):
    """Returns an authenticated client"""
    response = client.post(
        "/login/",
        data={
            "email": "ashley.cherian@gmail.com",
            "password": "admin"
        }
    )
    assert response.status_code == 303  # Redirect status
    assert "Authorization" in response.cookies
    return client, response.cookies["Authorization"]

c = TestClient(app)
def test_login_success():
    """Test successful login"""
    response = c.post(
        "/login/",
        data={
            "email": "ashley.cherian@gmail.com",
            "password": "admin"
        },follow_redirects=False
    )
    print(response)
    assert response.status_code == 303  # Should redirect
    assert "Authorization" in response.cookies