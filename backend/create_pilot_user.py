from app.database.database import create_user

try:
    create_user(
        user_id="pilot001",
        username="pilot1",
        password="Pilot@123",
        role="pilot"
    )

    print("Pilot user created successfully.")

except Exception as error:
    print("Error creating pilot user:", error)