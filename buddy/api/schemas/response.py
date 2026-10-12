from typing import Literal

from pydantic import BaseModel, ConfigDict


class ApiResponseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "fail"] = "fail"
    message: str = "invalid request"
