import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.internship import Application, Employer, InternshipListing, Offer, Student
from app.models.user import User
from app.repositories.internship import InternshipRepository


def test_employer_and_offer_flow():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        employer_user = User(username="employer", email="employer@example.com", password="pw", role="employer")
        student_user = User(username="student", email="student@example.com", password="pw", role="student")
        session.add_all([employer_user, student_user])
        session.commit()
        session.refresh(employer_user)
        session.refresh(student_user)

        repo = InternshipRepository(session)
        employer = repo.get_or_create_employer(employer_user.id, "Acme Labs", "Jane Foster")
        listing = repo.create_listing(
            employer_id=employer.employerID,
            title="Data Internship",
            description="Work with product analytics and dashboards.",
            is_paid=True,
        )
        student = repo.get_or_create_student(student_user.id, "Student Name")
        application = repo.create_application(
            student_id=student.studentID,
            listing_id=listing.listingID,
            cover_letter="I would love to contribute.",
        )
        offer = repo.create_offer(application_id=application.applicationID, start_date="2027-01-15")

        assert isinstance(employer, Employer)
        assert isinstance(listing, InternshipListing)
        assert isinstance(student, Student)
        assert isinstance(application, Application)
        assert isinstance(offer, Offer)
        assert offer.applicationID == application.applicationID
        assert offer.status == "pending"
        assert repo.db.get(Application, application.applicationID).status == "pending your decision"
        student_applications = repo.get_student_applications(student.studentID)
        assert student_applications[0]["status"] == "pending your decision"

        accepted_offer = repo.respond_to_offer(offer.offerID, "accepted")
        assert accepted_offer.status == "accepted"
        assert accepted_offer.applicationID == application.applicationID
        assert repo.db.get(Application, application.applicationID).status == "accepted"

        declined_offer = repo.respond_to_offer(offer.offerID, "declined")
        assert declined_offer.status == "declined"
        assert repo.db.get(Application, application.applicationID).status == "declined"


def test_employer_can_reject_application_and_rejected_application_cannot_receive_offer():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        employer_user = User(username="reject_employer", email="reject_employer@example.com", password="pw", role="employer")
        other_user = User(username="other_employer", email="other_employer@example.com", password="pw", role="employer")
        student_user = User(username="reject_student", email="reject_student@example.com", password="pw", role="student")
        session.add_all([employer_user, other_user, student_user])
        session.commit()
        session.refresh(employer_user)
        session.refresh(other_user)
        session.refresh(student_user)

        repo = InternshipRepository(session)
        employer = repo.get_or_create_employer(employer_user.id, "Acme", "Jane")
        other_employer = repo.get_or_create_employer(other_user.id, "Other Co", "Alex")
        student = repo.get_or_create_student(student_user.id, "Student")
        listing = repo.create_listing(employer.employerID, "Research Intern", "Research work", True)
        application = repo.create_application(student.studentID, listing.listingID, "Please consider me")

        with pytest.raises(ValueError, match="does not belong"):
            repo.reject_application(application.applicationID, other_employer.employerID)

        rejected = repo.reject_application(application.applicationID, employer.employerID)
        assert rejected.status == "rejected"
        with pytest.raises(ValueError, match="rejected"):
            repo.create_offer(application.applicationID, "2027-01-15")


def test_browsing_empty_database_does_not_create_demo_internships():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        repo = InternshipRepository(session)

        assert repo.find_open_listings() == []
        assert session.exec(select(Employer)).all() == []


def test_student_application_tracking_and_duplicate_prevention():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(username="student_user", email="student_user@example.com", password="pw", role="student")
        session.add(user)
        session.commit()
        session.refresh(user)

        repo = InternshipRepository(session)
        student = repo.get_or_create_student(user.id, "Student User")
        employer = repo.get_or_create_employer(99, "Acme", "Jane")
        listing_1 = repo.create_listing(employer.employerID, "One", "First internship", True)
        listing_2 = repo.create_listing(employer.employerID, "Two", "Second internship", False)

        app_1 = repo.create_application(student.studentID, listing_1.listingID, "I want this one")
        my_apps = repo.get_student_applications(student.studentID)

        assert [item["listing"].listingID for item in my_apps] == [listing_1.listingID]
        assert repo.get_applied_listing_ids(student.studentID) == {listing_1.listingID}

        with pytest.raises(ValueError, match="already applied"):
            repo.create_application(student.studentID, listing_1.listingID, "Again")

        assert app_1.applicationID is not None
        assert app_1.status == "submitted"


def test_application_can_store_document_metadata():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        user = User(username="student_doc", email="student_doc@example.com", password="pw", role="student")
        session.add(user)
        session.commit()
        session.refresh(user)

        repo = InternshipRepository(session)
        student = repo.get_or_create_student(user.id, "Student Doc")
        employer = repo.get_or_create_employer(999, "Acme", "Jane")
        listing = repo.create_listing(employer.employerID, "Research Internship", "Explore data and analysis work.", True)

        app = repo.create_application(
            student_id=student.studentID,
            listing_id=listing.listingID,
            cover_letter="I am excited to share my CV.",
            attachment_name="cv.pdf",
            attachment_path="uploads/cv.pdf",
        )

        assert app.documentName == "cv.pdf"
        assert app.documentPath == "uploads/cv.pdf"


def test_employer_can_edit_an_existing_listing():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        employer_user = User(username="employer_edit", email="employer_edit@example.com", password="pw", role="employer")
        session.add(employer_user)
        session.commit()
        session.refresh(employer_user)

        repo = InternshipRepository(session)
        employer = repo.get_or_create_employer(employer_user.id, "Acme Labs", "Jane Foster")
        listing = repo.create_listing(
            employer_id=employer.employerID,
            title="Old title",
            description="Old description",
            is_paid=False,
        )

        updated = repo.update_listing(
            listing_id=listing.listingID,
            title="Updated title",
            description="Updated description",
            is_paid=True,
        )

        assert updated.title == "Updated title"
        assert updated.description == "Updated description"
        assert updated.isPaid is True
        assert repo.db.get(InternshipListing, listing.listingID).title == "Updated title"


def test_employer_dashboard_hides_offer_form_after_offer_is_sent():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        employer_user = User(username="employer2", email="employer2@example.com", password="pw", role="employer")
        student_user = User(username="student2", email="student2@example.com", password="pw", role="student")
        session.add_all([employer_user, student_user])
        session.commit()
        session.refresh(employer_user)
        session.refresh(student_user)

        repo = InternshipRepository(session)
        employer = repo.get_or_create_employer(employer_user.id, "Acme Labs", "Jane Foster")
        listing = repo.create_listing(
            employer_id=employer.employerID,
            title="Product Internship",
            description="Design and validate user-facing workflows.",
            is_paid=True,
        )
        student = repo.get_or_create_student(student_user.id, "Student Two")
        application = repo.create_application(
            student_id=student.studentID,
            listing_id=listing.listingID,
            cover_letter="I am excited to work on this.",
        )

        first_offer = repo.create_offer(application.applicationID, "2027-02-01")
        rows = repo.get_listing_applications(listing.listingID)

        assert rows[0]["application"].applicationID == application.applicationID
        assert rows[0]["offer"] is not None
        assert rows[0]["offer"].offerID == first_offer.offerID

        with pytest.raises(ValueError, match="already exists"):
            repo.create_offer(application.applicationID, "2027-02-15")
