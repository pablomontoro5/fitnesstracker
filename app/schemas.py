from datetime import date
from pydantic import BaseModel, Field
class DailyLogCreate(BaseModel):
    date: date
    steps: int = Field(ge=0)
    notes: str | None = Field(default=None, max_length=1000)


class DailyLogUpdate(BaseModel):
    steps: int = Field(ge=0)
    notes: str | None = Field(default=None, max_length=1000)


class DailyLogResponse(BaseModel):
    id: int
    date: date
    steps: int
    notes: str | None