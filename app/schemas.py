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

class BodyMetricCreate(BaseModel):
    date: date
    weight_kg: float = Field(gt=0,le=500)
    height_cm: float = Field(gt=0,le=300)
    notes: str | None = Field(default=None, max_length=1000)

class BodyMetricResponse(BaseModel):
    id: int
    date: date
    weight_kg: float
    height_cm: float
    bmi: float
    notes: str | None