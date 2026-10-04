from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Request, status, Form
from app.dependencies import SessionDep
from . import router, templates
from app.services.auth_service import AuthService, normalize_role
from app.repositories.user import UserRepository
from app.utilities.flash import flash
from app.utilities.security import access_token_cookie_kwargs


@router.get("/login", response_class=HTMLResponse)
async def login_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
    )


@router.post("/login", response_class=HTMLResponse)
async def login_action_ajax(
    db: SessionDep,
    request: Request,
    username: str = Form(),
    password: str = Form(),
):
    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)
    access_token = auth_service.authenticate_user(username, password)
    if not access_token:
        flash(request, "Incorrect username or password", "danger")
        return RedirectResponse(
            url=request.url_for("login_view"),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    user = user_repo.get_by_username(username)
    user_role = normalize_role(user.role if user else "")
    if user_role == "employer":
        target_name = "employer_dashboard"
    elif user_role == "student":
        target_name = "student_activity"
    else:
        target_name = "browse_internships"
    response = RedirectResponse(
        url=request.url_for(target_name),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        **access_token_cookie_kwargs(),
    )
    return response
