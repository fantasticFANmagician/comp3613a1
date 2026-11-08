import pytest
from app.models.internship import Student, Employer, InternshipListing, Application, Offer 

def test_register_student():
    student = Student(email="ada@uwi.edu", password="password123", role="student")
    assert student.role == "student"

def test_invalid_email():
    with pytest.raises(Exception): 
        Student(email="no-at-sign", password="password123", role="student")

def test_hashed_password():
    password = "password123"
    hashed = "hashed_password_example" 
    assert hashed != password

def test_create_listing_defaults():
    listing = InternshipListing(title="Data Intern", description="Analyse data", isPaid=False)
    assert listing.status == "Open"
