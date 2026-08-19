from datetime import date
from pydantic import BaseModel, Field
from typing import Literal 

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

class BodyMetricUpdate(BaseModel):
    date: date
    weight_kg: float = Field(gt=0, le=500)
    height_cm: float = Field(gt=0, le=300)
    notes: str | None = Field(default=None, max_length=1000)

class WorkoutSessionCreate(BaseModel):
    date: date
    name: str = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)


class WorkoutSessionUpdate(BaseModel):
    date: date
    name: str = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)


class WorkoutSetUpdate(BaseModel):
    set_type: Literal["warmup", "approximation", "working", "drop_set"]
    position: int = Field(ge=1, le=100)
    target_rep_range: str | None = Field(default=None, max_length=30)
    repetitions: int = Field(gt=0, le=1000)
    weight_kg: float = Field(ge=0, le=1000)
    rir: float | None = Field(default=None, ge=-3, le=10)
    notes: str | None = Field(default=None, max_length=1000)


class WorkoutSessionResponse(BaseModel):
    id: int
    date: date
    name: str
    notes: str | None

class WorkoutExerciseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    muscle_group: str = Field(min_length=1, max_length=80)
    position: int = Field(ge=1, le=100)
    technique_notes: str | None = Field(default=None, max_length=2000)

class WorkoutExerciseUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    muscle_group: str = Field(min_length=1, max_length=80)
    position: int = Field(ge=1, le=100)
    technique_notes: str | None = Field(default=None, max_length=2000)
    
class WorkoutExerciseResponse(BaseModel):
    id: int
    workout_session_id: int
    name: str
    muscle_group: str
    position: int
    technique_notes: str | None

class WorkoutSetCreate(BaseModel):
    set_type: Literal["warmup", "approximation", "working", "drop_set"]
    position: int = Field(ge=1, le=100)
    target_rep_range: str | None = Field(default=None, max_length=30)
    repetitions: int = Field(gt=0, le=1000)
    weight_kg: float = Field(ge=0, le=1000)
    rir: float | None = Field(default=None, ge=-3, le=10)
    notes: str | None = Field(default=None, max_length=1000)


class WorkoutSetResponse(BaseModel):
    id: int
    workout_exercise_id: int
    set_type: Literal["warmup", "approximation", "working", "drop_set"]
    position: int
    target_rep_range: str | None
    repetitions: int
    weight_kg: float
    rir: float | None
    notes: str | None
    volume_kg: float

class WorkoutProgressSetResponse(BaseModel):
    id: int
    position: int
    repetitions: int
    weight_kg: float
    rir: float | None
    volume_kg: float


class WorkoutProgressSessionResponse(BaseModel):
    session_id: int
    session_name: str
    date: date
    total_volume_kg: float
    sets: list[WorkoutProgressSetResponse]


class WorkoutProgressResponse(BaseModel):
    exercise_name: str
    sessions: list[WorkoutProgressSessionResponse]

