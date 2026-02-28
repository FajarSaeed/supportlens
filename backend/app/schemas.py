from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

Category = Literal["Billing", "Refund", "Account Access", "Cancellation", "General Inquiry"]

class TraceCreate(BaseModel):
    user_message: str = Field(min_length=1)
    bot_response: str = Field(min_length=1)
    response_time_ms: int = Field(ge=0)

class TraceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_message: str
    bot_response: str
    category: str
    timestamp: datetime
    response_time_ms: int

    @field_serializer("category")
    def serialize_category(self, value: object) -> str:
        # value may be a models.Category enum or already a plain string
        return value.value if hasattr(value, "value") else str(value)

class AnalyticsOut(BaseModel):
    total_traces: int
    avg_response_time_ms: float
    by_category: dict  # {category: {"count": int, "percent": float}}

class ChatIn(BaseModel):
    user_message: str = Field(min_length=1)

class ChatOut(BaseModel):
    bot_response: str
    response_time_ms: int
