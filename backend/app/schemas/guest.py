"""Guest schemas."""

from pydantic import BaseModel


class GuestResponse(BaseModel):
    id: str
    name: str
    avatar: str
    description: str
    personality: str

    class Config:
        from_attributes = True
