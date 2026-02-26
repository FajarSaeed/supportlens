import enum
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Category(str, enum.Enum):
    Billing = "Billing"
    Refund = "Refund"
    AccountAccess = "Account Access"
    Cancellation = "Cancellation"
    GeneralInquiry = "General Inquiry"

class Trace(Base):
    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_message: Mapped[str] = mapped_column(String, nullable=False)
    bot_response: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[Category] = mapped_column(Enum(Category), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)