from typing import Literal

from pydantic import BaseModel, Field


class PermissionReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    review_comment: str = Field(min_length=3, max_length=500)