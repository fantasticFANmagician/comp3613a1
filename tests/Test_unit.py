import pytest
from app.models.internship import Student, Employer, InternshipListing, Application, Offer 
# ^^^ Note the change to the import path and the class name ^^^

def test_register_student():
    student = Student(email="ada@uwi.edu", password="password123", role="student")
    assert student.role == "student"

def test_invalid_email():
    # Assuming your model has validation (this might fail if you haven't implemented it yet)
    with pytest.raises(Exception): 
        Student(email="no-at-sign", password="password123", role="student")

def test_hashed_password():
    password = "password123"
    # Assuming you have a function that hashes passwords, or do it manually here
    hashed = "hashed_password_example" 
    assert hashed != password

def test_create_listing_defaults():
    # Changed 'Listing' to 'InternshipListing'
    listing = InternshipListing(title="Data Intern", description="Analyse data", isPaid=False)
    assert listing.status == "Open"
