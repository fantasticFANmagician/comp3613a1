from app.repositories.internship import InternshipRepository


class InternshipService:
    def __init__(self, internship_repo: InternshipRepository):
        self.internship_repo = internship_repo

    def browse_open_listings(self, title_filter: str = ""):
        return self.internship_repo.find_open_listings(title_filter.strip())

    def submit_application(
        self,
        user_id: int,
        username: str,
        listing_id: int,
        cover_letter: str,
        attachment_name: str | None = None,
        attachment_path: str | None = None,
    ):
        student = self.internship_repo.get_or_create_student(user_id, username)
        return self.internship_repo.create_application(
            student_id=student.studentID,
            listing_id=listing_id,
            cover_letter=cover_letter,
            attachment_name=attachment_name,
            attachment_path=attachment_path,
        )

    def get_employer_listings(self, employer_id: int):
        return self.internship_repo.get_employer_listings(employer_id)

    def create_listing(
        self,
        employer_id: int,
        title: str,
        description: str,
        is_paid: bool,
    ):
        return self.internship_repo.create_listing(
            employer_id=employer_id,
            title=title,
            description=description,
            is_paid=is_paid,
        )

    def close_listing(self, listing_id: int, status: str = "closed"):
        return self.internship_repo.update_listing_status(listing_id, status)

    def update_listing(self, listing_id: int, title: str, description: str, is_paid: bool):
        return self.internship_repo.update_listing(
            listing_id=listing_id,
            title=title,
            description=description,
            is_paid=is_paid,
        )

    def get_listing_applications(self, listing_id: int):
        return self.internship_repo.get_listing_applications(listing_id)

    def get_student_applications(self, user_id: int, username: str = ""):
        student = self.internship_repo.get_or_create_student(user_id, username or "Student")
        return self.internship_repo.get_student_applications(student.studentID)

    def get_applied_listing_ids(self, user_id: int, username: str = ""):
        student = self.internship_repo.get_or_create_student(user_id, username or "Student")
        return self.internship_repo.get_applied_listing_ids(student.studentID)

    def create_offer(self, application_id: int, start_date: str):
        return self.internship_repo.create_offer(application_id, start_date)

    def reject_application(self, application_id: int, employer_id: int):
        return self.internship_repo.reject_application(application_id, employer_id)

    def get_student_offers(self, user_id: int, username: str = ""):
        student = self.internship_repo.get_or_create_student(user_id, username or "Student")
        return self.internship_repo.get_student_offers(student.studentID)

    def respond_to_offer(self, offer_id: int, decision: str):
        return self.internship_repo.respond_to_offer(offer_id, decision)