from app.database.database import create_user


try:
    result = create_user(
        user_id="user123",
        username="admin",
        password="Admin@123",
        role="admin"
    )

    if result:
        print("Test user created successfully.")

except Exception as error:
    print("Unable to create test user.")
    print("Reason:", error)