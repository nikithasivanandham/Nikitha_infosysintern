from fastapi import APIRouter, HTTPException, status
from fastapi import Depends
from app.core.dependencies import get_current_user
from app.core.permissions import require_roles

from app.core.security import (
    create_access_token,
    verify_password
)

from app.database.database import get_user_by_username

from app.schemas.auth import (
    LoginRequest,
    TokenResponse
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(request: LoginRequest):

    user = get_user_by_username(request.username)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    password_valid = verify_password(
        request.password,
        user["hashed_password"]
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    access_token = create_access_token(
        user_id=user["user_id"],
        role=user["role"]
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )

@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user)
):
    return {
        "message": "Authentication successful",
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "role": current_user["role"]
    }
    
@router.get("/admin-only")
def admin_only(
    current_user: dict = Depends(require_roles("admin"))
):
    return {
        "message": "Admin access granted",
        "username": current_user["username"],
        "role": current_user["role"]
    }