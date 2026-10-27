from fastapi import Depends, HTTPException, status

from app.core.dependencies import get_current_user


def require_roles(*allowed_roles: str):
    def role_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:

        user_role = current_user.get("role")

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )

        return current_user

    return role_checker