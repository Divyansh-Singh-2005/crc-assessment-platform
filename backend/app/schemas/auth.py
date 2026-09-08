"""Authentication and user schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole

MIN_PASSWORD_LENGTH = 12


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=72)
    role: UserRole = UserRole.VIEWER

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        """Composition rules are enforced server side.

        Client-side validation is a usability feature, not a control: anything
        that can be bypassed with curl is not an access control.
        """
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password is too long once UTF-8 encoded (72 byte maximum)")
        if not any(character.isupper() for character in value):
            raise ValueError("Password must contain an uppercase letter")
        if not any(character.islower() for character in value):
            raise ValueError("Password must contain a lowercase letter")
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain a digit")
        return value


class UserRead(BaseModel):
    """Response model. Note the absence of password_hash: the field cannot be
    serialised out of the API because it is not declared here."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime