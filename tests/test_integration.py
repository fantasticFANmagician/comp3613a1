# tests/test_integration.py
from fastapi.testclient import TestClient
from app.main import app  # Adjust this if your app is located elsewhere

client = TestClient(app)

def test_login_token_grants_access():
    # 1. Register a user (FastAPI expects form data, not JSON)
    client.post("/register", data={
        "username": "testuser", 
        "email": "test@test.com", 
        "password": "password123", 
        "role": "student"
    })
    
    # 2. Attempt Login
    response = client.post("/login", data={
        "username": "testuser", 
        "password": "password123"
    }, follow_redirects=False) # Don't follow redirects so we can check the cookie
    
    # 3. Assertions
    assert response.status_code == 303 # FastAPI returns 303 on successful form login
    assert "access_token" in response.cookies # Verify the cookie was set

def test_post_then_browse():
    # 1. Register & Login as employer
    client.post("/register", data={"username": "boss", "email": "boss@test.com", "password": "pass", "role": "employer"})
    client.post("/login", data={"username": "boss", "password": "pass"})
    
    # 2. Post a listing
    client.post("/listings", data={"title": "Software Intern", "description": "Code", "isPaid": "true"})
    
    # 3. Register & Login as student
    client.post("/register", data={"username": "stud", "email": "stud@test.com", "password": "pass", "role": "student"})
    client.post("/login", data={"username": "stud", "password": "pass"})
    
    # 4. Browse listings
    response = client.get("/browse")
    assert response.status_code == 200
    # Assuming your HTML template displays the title
    assert "Software Intern" in response.text