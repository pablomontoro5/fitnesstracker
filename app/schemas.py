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

class RecoveryLogCreate(BaseModel):
    date: date
    sleep_minutes: int | None = Field(
        default=None,
        ge=0,
        le=1440,
    )
    sleep_quality: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )
    is_rest_day: bool = False
    notes: str | None = Field(default=None, max_length=1000)


class RecoveryLogUpdate(BaseModel):
    sleep_minutes: int | None = Field(
        default=None,
        ge=0,
        le=1440,
    )
    sleep_quality: int | None = Field(
        default=None,
        ge=1,
        le=5,
    )
    is_rest_day: bool = False
    notes: str | None = Field(default=None, max_length=1000)


class RecoveryLogResponse(BaseModel):
    id: int
    date: date
    sleep_minutes: int | None
    sleep_quality: int | None
    is_rest_day: bool
    notes: str | None

class BodyMetricCreate(BaseModel):
    date: date
    weight_kg: float = Field(gt=0, le=500)
    height_cm: float = Field(gt=0, le=300)
    body_fat_percentage: float | None = Field(
        default=None,
        gt=0,
        lt=100,
    )
    waist_cm: float | None = Field(default=None, gt=0, le=300)
    hip_cm: float | None = Field(default=None, gt=0, le=300)
    chest_cm: float | None = Field(default=None, gt=0, le=300)
    arm_cm: float | None = Field(default=None, gt=0, le=200)
    thigh_cm: float | None = Field(default=None, gt=0, le=300)
    notes: str | None = Field(default=None, max_length=1000)


class BodyMetricResponse(BaseModel):
    id: int
    date: date
    weight_kg: float
    height_cm: float
    bmi: float
    body_fat_percentage: float | None
    fat_mass_kg: float | None
    lean_mass_kg: float | None
    waist_cm: float | None
    hip_cm: float | None
    chest_cm: float | None
    arm_cm: float | None
    thigh_cm: float | None
    notes: str | None


class BodyMetricUpdate(BaseModel):
    date: date
    weight_kg: float = Field(gt=0, le=500)
    height_cm: float = Field(gt=0, le=300)
    body_fat_percentage: float | None = Field(
        default=None,
        gt=0,
        lt=100,
    )
    waist_cm: float | None = Field(default=None, gt=0, le=300)
    hip_cm: float | None = Field(default=None, gt=0, le=300)
    chest_cm: float | None = Field(default=None, gt=0, le=300)
    arm_cm: float | None = Field(default=None, gt=0, le=200)
    thigh_cm: float | None = Field(default=None, gt=0, le=300)
    notes: str | None = Field(default=None, max_length=1000)


class BodyCompositionProgressRecord(BaseModel):
    date: date
    weight_kg: float
    bmi: float
    body_fat_percentage: float | None
    fat_mass_kg: float | None
    lean_mass_kg: float | None
    waist_cm: float | None
    hip_cm: float | None
    chest_cm: float | None
    arm_cm: float | None
    thigh_cm: float | None


class BodyCompositionChanges(BaseModel):
    weight_kg: float | None
    bmi: float | None
    body_fat_percentage: float | None
    fat_mass_kg: float | None
    lean_mass_kg: float | None
    waist_cm: float | None
    hip_cm: float | None
    chest_cm: float | None
    arm_cm: float | None
    thigh_cm: float | None


class BodyCompositionProgressResponse(BaseModel):
    start_date: date
    end_date: date
    records: list[BodyCompositionProgressRecord]
    changes: BodyCompositionChanges
    
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
    working_sets: int
    total_repetitions: int
    total_volume_kg: float
    max_weight_kg: float
    max_volume_set_kg: float
    sets: list[WorkoutProgressSetResponse]


class WorkoutProgressResponse(BaseModel):
    exercise_name: str
    sessions: list[WorkoutProgressSessionResponse]

PersonalRecordMetric = Literal[
    "max_weight_kg",
    "max_repetitions",
    "max_set_volume_kg",
    "estimated_one_rep_max_kg",
    "max_session_volume_kg",
]


class WorkoutPersonalRecord(BaseModel):
    metric: PersonalRecordMetric
    label: str
    value: float
    unit: str
    date: date
    session_id: int
    session_name: str
    set_id: int | None
    repetitions: int | None
    weight_kg: float | None
    volume_kg: float | None


class WorkoutPersonalRecordsExerciseResponse(BaseModel):
    exercise_name: str
    records: list[WorkoutPersonalRecord]


class RunCreate(BaseModel):
    date: date
    distance_km: float = Field(gt=0, le=1000)
    duration_seconds: int = Field(gt=0, le=172800)
    notes: str | None = Field(default=None, max_length=1000)


class RunUpdate(BaseModel):
    date: date
    distance_km: float = Field(gt=0, le=1000)
    duration_seconds: int = Field(gt=0, le=172800)
    notes: str | None = Field(default=None, max_length=1000)


class RunResponse(BaseModel):
    id: int
    date: date
    distance_km: float
    duration_seconds: int
    average_pace_seconds_km: float
    notes: str | None

class StatisticsStepsResponse(BaseModel):
    total: int
    days_logged: int
    average_per_logged_day: float


class StatisticsWorkoutsResponse(BaseModel):
    sessions: int
    exercises: int
    working_sets: int
    repetitions: int
    volume_kg: float


class StatisticsRunningResponse(BaseModel):
    runs: int
    distance_km: float
    duration_seconds: int
    average_pace_seconds_km: float | None


class StatisticsBodyMetricResponse(BaseModel):
    date: date
    weight_kg: float
    height_cm: float
    bmi: float


class StatisticsBodyMetricsResponse(BaseModel):
    records: int
    latest: StatisticsBodyMetricResponse | None
    weight_change_kg: float | None


class ActivityStatisticsResponse(BaseModel):
    start_date: date
    end_date: date
    steps: StatisticsStepsResponse
    workouts: StatisticsWorkoutsResponse
    running: StatisticsRunningResponse
    body_metrics: StatisticsBodyMetricsResponse

class NutritionDayCreate(BaseModel):
    date: date
    notes: str | None = Field(default=None, max_length=1000)


class NutritionDayUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)


class NutritionDayResponse(BaseModel):
    id: int
    date: date
    notes: str | None

class NutritionMealCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    position: int = Field(ge=1, le=20)


class NutritionMealUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    position: int = Field(ge=1, le=20)


class NutritionMealResponse(BaseModel):
    id: int
    nutrition_day_id: int
    name: str
    position: int

class NutritionFoodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity_g: float = Field(gt=0, le=10000)
    calories: float = Field(ge=0, le=50000)
    protein_g: float = Field(ge=0, le=10000)
    carbs_g: float = Field(ge=0, le=10000)
    fat_g: float = Field(ge=0, le=10000)
    position: int = Field(ge=1, le=100)
    notes: str | None = Field(default=None, max_length=1000)


class NutritionFoodUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity_g: float = Field(gt=0, le=10000)
    calories: float = Field(ge=0, le=50000)
    protein_g: float = Field(ge=0, le=10000)
    carbs_g: float = Field(ge=0, le=10000)
    fat_g: float = Field(ge=0, le=10000)
    position: int = Field(ge=1, le=100)
    notes: str | None = Field(default=None, max_length=1000)


class NutritionFoodResponse(BaseModel):
    id: int
    nutrition_meal_id: int
    name: str
    quantity_g: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    position: int
    notes: str | None

class StatisticsStepsChartPoint(BaseModel):
    date: date
    steps: int


class StatisticsWeightChartPoint(BaseModel):
    date: date
    weight_kg: float


class StatisticsRunningChartPoint(BaseModel):
    date: date
    distance_km: float


class ActivityChartsResponse(BaseModel):
    start_date: date
    end_date: date
    steps: list[StatisticsStepsChartPoint]
    weight: list[StatisticsWeightChartPoint]
    running: list[StatisticsRunningChartPoint]

class WorkoutTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=1000)


class WorkoutTemplateResponse(BaseModel):
    id: int
    name: str
    notes: str | None

class WorkoutTemplateExerciseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    muscle_group: str = Field(min_length=1, max_length=80)
    position: int = Field(ge=1, le=100)
    technique_notes: str | None = Field(default=None, max_length=2000)


class WorkoutTemplateExerciseUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    muscle_group: str = Field(min_length=1, max_length=80)
    position: int = Field(ge=1, le=100)
    technique_notes: str | None = Field(default=None, max_length=2000)


class WorkoutTemplateExerciseResponse(BaseModel):
    id: int
    workout_template_id: int
    name: str
    muscle_group: str
    position: int
    technique_notes: str | None

class WorkoutTemplateSetCreate(BaseModel):
    set_type: Literal["warmup", "approximation", "working", "drop_set"]
    position: int = Field(ge=1, le=100)
    target_rep_range: str | None = Field(default=None, max_length=30)
    repetitions: int = Field(gt=0, le=1000)
    weight_kg: float = Field(ge=0, le=1000)
    rir: float | None = Field(default=None, ge=-3, le=10)
    notes: str | None = Field(default=None, max_length=1000)


class WorkoutTemplateSetUpdate(BaseModel):
    set_type: Literal["warmup", "approximation", "working", "drop_set"]
    position: int = Field(ge=1, le=100)
    target_rep_range: str | None = Field(default=None, max_length=30)
    repetitions: int = Field(gt=0, le=1000)
    weight_kg: float = Field(ge=0, le=1000)
    rir: float | None = Field(default=None, ge=-3, le=10)
    notes: str | None = Field(default=None, max_length=1000)


class WorkoutTemplateSetResponse(BaseModel):
    id: int
    workout_template_exercise_id: int
    set_type: Literal["warmup", "approximation", "working", "drop_set"]
    position: int
    target_rep_range: str | None
    repetitions: int
    weight_kg: float
    rir: float | None
    notes: str | None
    volume_kg: float

GoalType = Literal[
    "daily_steps",
    "weekly_workouts",
    "weekly_running_km",
    "daily_calories",
    "daily_protein_g",
    "daily_carbs_g",
    "daily_fat_g",
    "daily_sleep_minutes",
    "weekly_rest_days",
]


class FitnessGoalUpsert(BaseModel):
    target_value: float = Field(gt=0, le=1_000_000)


class FitnessGoalResponse(BaseModel):
    id: int
    goal_type: GoalType
    target_value: float


class FitnessGoalProgressResponse(BaseModel):
    goal_type: GoalType
    target_value: float
    current_value: float
    progress_percentage: float
    is_completed: bool

class NutritionGoalProgressItem(BaseModel):
    current_value: float
    target_value: float | None
    remaining_value: float | None
    progress_percentage: float | None
    is_completed: bool


class NutritionGoalsProgressResponse(BaseModel):
    date: date
    calories: NutritionGoalProgressItem
    protein_g: NutritionGoalProgressItem
    carbs_g: NutritionGoalProgressItem
    fat_g: NutritionGoalProgressItem

class UserRegister(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=128)


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    is_active: bool
    created_at: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"