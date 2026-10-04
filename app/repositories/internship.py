from datetime import date

from sqlmodel import Session, select

from app.models.internship import Application, Employer, InternshipListing, Offer, Student


class InternshipRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_employer(self, user_id: int, company_name: str = "", contact_name: str = "") -> Employer:
        employer = self.db.exec(select(Employer).where(Employer.user_id == user_id)).one_or_none()
        if employer is not None:
            return employer

        employer = Employer(
            user_id=user_id,
            companyName=company_name or "Your company",
            contactName=contact_name or "Company contact",
        )
        self.db.add(employer)
        self.db.commit()
        self.db.refresh(employer)
        return employer

    def find_open_listings(self, title_filter: str = "") -> list[InternshipListing]:
        statement = select(InternshipListing).where(InternshipListing.status == "open")
        filter_text = (title_filter or "").strip()
        if filter_text:
            statement = statement.where(InternshipListing.title.ilike(f"%{filter_text}%"))

        return self.db.exec(statement).all()

    def get_or_create_student(self, user_id: int, username: str) -> Student:
        student = self.db.exec(select(Student).where(Student.user_id == user_id)).one_or_none()
        if student is not None:
            return student

        student = Student(
            user_id=user_id,
            fullName=username,
            university="",
            major="",
            resume="",
        )
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student)
        return student

    def create_listing(
        self,
        employer_id: int,
        title: str,
        description: str,
        is_paid: bool,
        status: str = "open",
    ) -> InternshipListing:
        listing = InternshipListing(
            employerID=employer_id,
            title=title.strip(),
            description=description.strip(),
            isPaid=is_paid,
            status=status,
            dayPosted=date.today(),
        )
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def get_employer_listings(self, employer_id: int) -> list[InternshipListing]:
        return self.db.exec(
            select(InternshipListing)
            .where(InternshipListing.employerID == employer_id)
            .order_by(InternshipListing.dayPosted.desc())
        ).all()

    def update_listing(
        self,
        listing_id: int,
        title: str,
        description: str,
        is_paid: bool,
    ) -> InternshipListing:
        listing = self.db.get(InternshipListing, listing_id)
        if listing is None:
            raise ValueError("Listing not found")

        listing.title = title.strip()
        listing.description = description.strip()
        listing.isPaid = is_paid
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def get_listing_applications(self, listing_id: int):
        applications = self.db.exec(select(Application).where(Application.listingID == listing_id)).all()
        rows = []
        for application in applications:
            student = self.db.get(Student, application.studentID)
            offer = self.db.exec(select(Offer).where(Offer.applicationID == application.applicationID)).first()
            rows.append({"application": application, "student": student, "offer": offer})
        return rows

    def get_student_applications(self, student_id: int):
        student = self.db.get(Student, student_id)
        if student is None:
            return []

        applications = self.db.exec(
            select(Application)
            .where(Application.studentID == student_id)
            .order_by(Application.dateSubmitted.desc())
        ).all()

        rows = []
        for application in applications:
            listing = self.db.get(InternshipListing, application.listingID)
            offer = self.db.exec(
                select(Offer).where(Offer.applicationID == application.applicationID)
            ).first()
            application_status = (
                "pending your decision"
                if offer is not None and offer.status == "pending"
                else application.status
            )
            rows.append({
                "application": application,
                "listing": listing,
                "status": application_status,
            })
        return rows

    def get_applied_listing_ids(self, student_id: int) -> set[int]:
        student = self.db.get(Student, student_id)
        if student is None:
            return set()

        applications = self.db.exec(
            select(Application.listingID).where(Application.studentID == student_id)
        ).all()
        return set(applications)

    def update_listing_status(self, listing_id: int, status: str) -> InternshipListing:
        listing = self.db.get(InternshipListing, listing_id)
        if listing is None:
            raise ValueError("Listing not found")
        listing.status = status
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def create_application(
        self,
        student_id: int,
        listing_id: int,
        cover_letter: str,
        attachment_name: str | None = None,
        attachment_path: str | None = None,
    ) -> Application:
        listing = self.db.get(InternshipListing, listing_id)
        if listing is None:
            raise ValueError("Listing not found")
        if listing.status != "open":
            raise ValueError("Listing is not open")

        existing = self.db.exec(
            select(Application).where(
                Application.studentID == student_id,
                Application.listingID == listing_id,
            )
        ).first()
        if existing is not None:
            raise ValueError("You have already applied to this listing")

        application = Application(
            studentID=student_id,
            listingID=listing_id,
            coverLetter=cover_letter,
            documentName=attachment_name,
            documentPath=attachment_path,
            status="submitted",
        )
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def create_offer(self, application_id: int, start_date: str) -> Offer:
        application = self.db.get(Application, application_id)
        if application is None:
            raise ValueError("Application not found")
        if application.status == "rejected":
            raise ValueError("Cannot send an offer to a rejected application")

        existing = self.db.exec(select(Offer).where(Offer.applicationID == application_id)).first()
        if existing is not None:
            raise ValueError("An offer already exists for this application")

        offer = Offer(
            applicationID=application_id,
            startDate=date.fromisoformat(start_date),
            status="pending",
        )
        application.status = "pending your decision"
        self.db.add(application)
        self.db.add(offer)
        self.db.commit()
        self.db.refresh(offer)
        return offer

    def reject_application(self, application_id: int, employer_id: int) -> Application:
        application = self.db.get(Application, application_id)
        if application is None:
            raise ValueError("Application not found")

        listing = self.db.get(InternshipListing, application.listingID)
        if listing is None or listing.employerID != employer_id:
            raise ValueError("Application does not belong to this employer")

        existing_offer = self.db.exec(
            select(Offer).where(Offer.applicationID == application_id)
        ).first()
        if existing_offer is not None:
            raise ValueError("Cannot reject an application after an offer has been sent")
        if application.status not in {"submitted", "under review"}:
            raise ValueError("Application cannot be rejected in its current status")

        application.status = "rejected"
        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def get_student_offers(self, student_id: int):
        offers = self.db.exec(
            select(Offer)
            .join(Application, Offer.applicationID == Application.applicationID)
            .where(Application.studentID == student_id)
            .order_by(Offer.dateSent.desc())
        ).all()
        rows = []
        for offer in offers:
            application = self.db.get(Application, offer.applicationID)
            listing = self.db.get(InternshipListing, application.listingID) if application else None
            rows.append({
                "offer": offer,
                "application": application,
                "listing": listing,
            })
        return rows

    def respond_to_offer(self, offer_id: int, decision: str) -> Offer:
        offer = self.db.get(Offer, offer_id)
        if offer is None:
            raise ValueError("Offer not found")

        normalized = (decision or "").strip().lower()
        if normalized not in {"accepted", "declined"}:
            raise ValueError("Decision must be accepted or declined")

        application = self.db.get(Application, offer.applicationID)
        if application is None:
            raise ValueError("Application not found")

        offer.status = normalized
        application.status = normalized
        self.db.add(offer)
        self.db.add(application)
        self.db.commit()
        self.db.refresh(offer)
        self.db.refresh(application)
        return offer
