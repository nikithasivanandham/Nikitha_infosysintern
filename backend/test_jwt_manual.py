from app.core.security import (
    create_access_token,
    verify_access_token
)


token = create_access_token(
    user_id="user123",
    role="admin"
)

print("Token generated:", bool(token))

payload = verify_access_token(token)

if payload:
    print("Token verification successful")
    print("User ID:", payload["sub"])
    print("Role:", payload["role"])
else:
    print("Token verification failed")