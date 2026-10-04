from app.repositories.user import UserRepository
from app.utilities.security import encrypt_password, verify_password, create_access_token
from app.schemas.user import RegularUserCreate
from typing import Optional


def normalize_role(role: str | None) -> str:
    if role is None:
        return "student"

    value = str(role).strip().lower()
    if value in {"student", "regular_user"}:
        return "student"
    if value in {"employer", "admin"}:
        return value
    return "student"


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        user = self.user_repo.get_by_username(username)
        if not user or not verify_password(plaintext_password=password, encrypted_password=user.password):
            return None
        access_token = create_access_token(data={"sub": f"{user.id}", "role": normalize_role(user.role)})
        return access_token

    def register_user(self, username: str, email: str, password: str, role: str = "student"):
        normalized_role = normalize_role(role)
        new_user = RegularUserCreate(
            username=username,
            email=email,
            password=encrypt_password(password),
            role=normalized_role,
        )
        return self.user_repo.create(new_user)
