from pydantic import BaseModel, Field


class PermissionRequestCreate(BaseModel):
    flight_number: str = Field(min_length=1, max_length=20)
    requested_action: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=5, max_length=500)


class PermissionRequestResponse(BaseModel):
    request_id: str
    pilot_user_id: str
    flight_number: str
    requested_action: str
    reason: str
    status: str