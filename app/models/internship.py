from datetime import date
from typing import Optional

from pydantic import EmailStr
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Student(SQLModel, table=True):
    __tablename__ = "student"

    studentID: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=0, foreign_key="user.id", unique=True)
    fullName: str = ""
    university: str = ""
    major: str = ""
    resume: str = ""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: str = "student"

    def __init__(self, **data: object):
        email = data.get("email")
        if email is not None and (
            not isinstance(email, str)
            or "@" not in email
            or email.startswith("@")
            or email.endswith("@")
        ):
            raise ValueError("Invalid email address")
        super().__init__(**data)


class Employer(SQLModel, table=True):
    __tablename__ = "employer"

    employerID: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    companyName: str
    contactName: str


class InternshipListing(SQLModel, table=True):
    __tablename__ = "internship_listing"

    listingID: Optional[int] = Field(default=None, primary_key=True)
    employerID: int = Field(foreign_key="employer.employerID")
    title: str
    description: str
    isPaid: bool
    status: str = "Open"
    dayPosted: date = Field(default_factory=date.today)


class Application(SQLModel, table=True):
    __tablename__ = "application"
    __table_args__ = (
        UniqueConstraint("studentID", "listingID", name="uq_application_student_listing"),
    )

    applicationID: Optional[int] = Field(default=None, primary_key=True)
    studentID: int = Field(foreign_key="student.studentID")
    listingID: int = Field(foreign_key="internship_listing.listingID")
    coverLetter: str
    documentName: Optional[str] = None
    documentPath: Optional[str] = None
    dateSubmitted: date = Field(default_factory=date.today)
    status: str = "submitted"


class Offer(SQLModel, table=True):
    __tablename__ = "offer"

    offerID: Optional[int] = Field(default=None, primary_key=True)
    applicationID: int = Field(foreign_key="application.applicationID", unique=True)
    dateSent: date = Field(default_factory=date.today)
    startDate: date
    status: str = "pending"