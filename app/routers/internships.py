from pathlib import Path
from uuid import uuid4

from fastapi import File, Form, Request, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.dependencies.auth import AuthDep
from app.dependencies.session import SessionDep
from app.models.internship import Application, InternshipListing
from app.repositories.internship import InternshipRepository
from app.services.internship_service import InternshipService
from app.utilities.flash import flash

from . import router, templates


UPLOADS_DIR = Path("uploads")


async def save_application_document(document: UploadFile | None) -> tuple[str | None, str | None]:
    if document is None or not document.filename:
        return None, None

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    original_name = Path(document.filename).name
    unique_name = f"{uuid4().hex}_{original_name}"
    destination = UPLOADS_DIR / unique_name

    with destination.open("wb") as file_handle:
        while chunk := await document.read(1024 * 1024):
            file_handle.write(chunk)

    await document.close()
    return original_name, str(destination)


@router.get("/internships", response_class=HTMLResponse, name="browse_internships")
async def browse_internships(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    q: str | None = None,
):
    if user.role == "employer":
        return RedirectResponse(
            url=request.url_for("employer_dashboard"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    listings = internship_service.browse_open_listings(q or "")
    applied_listing_ids = set()
    if user.role == "student":
        applied_listing_ids = internship_service.get_applied_listing_ids(user.id, user.username)
    return templates.TemplateResponse(
        request=request,
        name="internships.html",
        context={
            "user": user,
            "listings": listings,
            "query": q or "",
            "applied_listing_ids": applied_listing_ids,
        },
    )


@router.get("/student/activity", response_class=HTMLResponse, name="student_activity")
async def student_activity(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    view: str = "applications",
):
    if user.role != "student":
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    internship_service = InternshipService(InternshipRepository(db))
    active_view = "offers" if view == "offers" else "applications"
    return templates.TemplateResponse(
        request=request,
        name="student_activity.html",
        context={
            "user": user,
            "active_view": active_view,
            "student_applications": internship_service.get_student_applications(user.id, user.username),
            "student_offers": internship_service.get_student_offers(user.id, user.username),
        },
    )


@router.get("/employer/dashboard", response_class=HTMLResponse, name="employer_dashboard")
async def employer_dashboard(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    if user.role != "employer":
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    employer = internship_repo.get_or_create_employer(user.id, company_name=user.username, contact_name=user.username)
    listings = internship_service.get_employer_listings(employer.employerID)
    rows = []
    for listing in listings:
        rows.append({
            "listing": listing,
            "applications": internship_service.get_listing_applications(listing.listingID),
        })
    return templates.TemplateResponse(
        request=request,
        name="employer_dashboard.html",
        context={
            "user": user,
            "listings": rows,
        },
    )


@router.get("/employer/applicants", response_class=HTMLResponse, name="employer_applicants")
async def employer_applicants(
    request: Request,
    user: AuthDep,
    db: SessionDep,
):
    if user.role != "employer":
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    employer = internship_repo.get_or_create_employer(user.id, company_name=user.username, contact_name=user.username)
    listings = internship_service.get_employer_listings(employer.employerID)
    applicant_groups = []
    for listing in listings:
        applicant_groups.append({
            "listing": listing,
            "applications": internship_service.get_listing_applications(listing.listingID),
        })

    return templates.TemplateResponse(
        request=request,
        name="employer_applicants.html",
        context={
            "user": user,
            "groups": applicant_groups,
        },
    )


@router.get("/employer/listings/{listing_id}/applicants", response_class=HTMLResponse, name="listing_applicants")
async def listing_applicants(
    request: Request,
    listing_id: int,
    user: AuthDep,
    db: SessionDep,
):
    if user.role != "employer":
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    employer = internship_repo.get_or_create_employer(user.id, company_name=user.username, contact_name=user.username)
    listing = internship_repo.db.get(InternshipListing, listing_id)
    if listing is None or listing.employerID != employer.employerID:
        return RedirectResponse(
            url=request.url_for("employer_dashboard"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    applications = internship_service.get_listing_applications(listing.listingID)
    return templates.TemplateResponse(
        request=request,
        name="listing_applicants.html",
        context={
            "user": user,
            "listing": listing,
            "applications": applications,
        },
    )


@router.post("/employer/listings", name="create_listing")
async def create_listing(
    request: Request,
    user: AuthDep,
    db: SessionDep,
    title: str = Form(...),
    description: str = Form(...),
    is_paid: bool = Form(False),
):
    if user.role != "employer":
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    employer = internship_repo.get_or_create_employer(user.id, company_name=user.username, contact_name=user.username)
    internship_service.create_listing(
        employer_id=employer.employerID,
        title=title,
        description=description,
        is_paid=is_paid,
    )
    flash(request, "Internship listing posted", "success")
    return RedirectResponse(
        url=request.url_for("employer_dashboard"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/employer/listings/{listing_id}/close", name="close_listing")
async def close_listing(
    request: Request,
    listing_id: int,
    user: AuthDep,
    db: SessionDep,
):
    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    listing = internship_repo.db.get(InternshipListing, listing_id)
    current_status = listing.status if listing is not None else "open"
    next_status = "open" if current_status == "closed" else "closed"
    internship_service.close_listing(listing_id, next_status)
    flash(request, f"Listing {next_status}", "success")
    return RedirectResponse(
        url=request.url_for("employer_dashboard"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/employer/listings/{listing_id}/edit", name="edit_listing")
async def edit_listing(
    request: Request,
    listing_id: int,
    user: AuthDep,
    db: SessionDep,
    title: str = Form(...),
    description: str = Form(...),
    is_paid: bool = Form(False),
):
    if user.role != "employer":
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    try:
        internship_service.update_listing(
            listing_id=listing_id,
            title=title,
            description=description,
            is_paid=is_paid,
        )
        flash(request, "Listing updated", "success")
    except ValueError as exc:
        flash(request, str(exc), "warning")
    return RedirectResponse(
        url=request.url_for("employer_dashboard"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/employer/applications/{application_id}/offer", name="create_offer")
async def create_offer(
    request: Request,
    application_id: int,
    user: AuthDep,
    db: SessionDep,
    start_date: str = Form(...),
):
    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    try:
        internship_service.create_offer(application_id, start_date)
        flash(request, "Offer sent", "success")
    except ValueError as exc:
        flash(request, str(exc), "warning")

    return RedirectResponse(
        url=request.url_for("employer_applicants"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/employer/applications/{application_id}/reject", name="reject_application")
async def reject_application(
    request: Request,
    application_id: int,
    user: AuthDep,
    db: SessionDep,
):
    if user.role != "employer":
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    employer = internship_repo.get_or_create_employer(user.id, company_name=user.username, contact_name=user.username)
    try:
        internship_service.reject_application(application_id, employer.employerID)
        flash(request, "Application rejected", "success")
    except ValueError as exc:
        flash(request, str(exc), "warning")

    return RedirectResponse(
        url=request.url_for("employer_applicants"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/internships/{listing_id}/apply", name="apply_to_internship")
async def apply_to_internship(
    request: Request,
    listing_id: int,
    user: AuthDep,
    db: SessionDep,
    cover_letter: str = Form(""),
    document: UploadFile | None = File(None),
):
    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    file_name, file_path = await save_application_document(document)
    try:
        internship_service.submit_application(
            user_id=user.id,
            username=user.username,
            listing_id=listing_id,
            cover_letter=cover_letter,
            attachment_name=file_name,
            attachment_path=file_path,
        )
        flash(request, "Application submitted", "success")
    except ValueError as exc:
        flash(request, str(exc), "warning")
        if file_path and Path(file_path).exists():
            Path(file_path).unlink(missing_ok=True)
    return RedirectResponse(
        url=request.url_for("browse_internships"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/employer/applications/{application_id}/attachment", name="download_application_attachment")
async def download_application_attachment(
    request: Request,
    application_id: int,
    user: AuthDep,
    db: SessionDep,
):
    if user.role != "employer":
        return RedirectResponse(
            url=request.url_for("browse_internships"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    internship_repo = InternshipRepository(db)
    application = internship_repo.db.get(Application, application_id)
    if application is None:
        return RedirectResponse(
            url=request.url_for("employer_applicants"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    listing = internship_repo.db.get(InternshipListing, application.listingID)
    employer = internship_repo.get_or_create_employer(user.id, company_name=user.username, contact_name=user.username)
    if listing is None or listing.employerID != employer.employerID:
        return RedirectResponse(
            url=request.url_for("employer_applicants"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    document_path = application.documentPath
    if not document_path or not Path(document_path).exists():
        return RedirectResponse(
            url=request.url_for("employer_applicants"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return FileResponse(
        path=str(document_path),
        filename=application.documentName or "application-document",
        media_type="application/octet-stream",
    )


@router.post("/internships/offers/{offer_id}/respond", name="respond_to_offer")
async def respond_to_offer(
    request: Request,
    offer_id: int,
    user: AuthDep,
    db: SessionDep,
    response: str = Form(...),
):
    internship_repo = InternshipRepository(db)
    internship_service = InternshipService(internship_repo)
    try:
        internship_service.respond_to_offer(offer_id, response)
        flash(request, f"Offer {response}", "success")
    except ValueError as exc:
        flash(request, str(exc), "warning")
    return RedirectResponse(
        url=request.url_for("student_activity").include_query_params(view="offers"),
        status_code=status.HTTP_303_SEE_OTHER,
    )