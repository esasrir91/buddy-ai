from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, EmailStr, model_validator


class UserSchema(BaseModel):
    """Schema for user data returned by the API."""

    id_user: str
    email: Optional[str] = None
    username: Optional[str] = None
    name: Optional[str] = None
    email_verified: bool = False
    is_active: bool = True
    is_machine: bool = False
    user_data: Optional[Dict[str, Any]] = None


class EmailPasswordAuthSchema(BaseModel):
    email: EmailStr
    password: str
    auth_source: Literal["cli"] = "cli"


class TeamSchema(BaseModel):
    """Schema for team data returned by the API."""

    id_team: str
    name: str
    url: str


class TeamIdentifier(BaseModel):
    id_team: Optional[str] = None
    team_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_identifier(self) -> "TeamIdentifier":
        if not self.id_team and not self.team_url:
            raise ValueError("At least one of id_team or team_url is required")
        return self
