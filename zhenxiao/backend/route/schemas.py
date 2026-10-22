"""Pydantic 请求/响应模型。"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="当前用户消息")
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    patient_context: Optional[dict] = None
    enable_deep_search: bool = True


class ChatResponse(BaseModel):
    session_id: str
    scene: str
    answer: str
    recommended_department: Optional[str] = None
    risk_level: Optional[str] = None
    evidence: list = []
    disclaimer: str = ""
    metrics: dict = {}
    trace: list = []
    thinking_steps: list = []
    red_flags: list = []
    follow_up_questions: list = []
    health_advice: list = []


class HealthProfileIn(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    chronic_diseases: Optional[str] = None
    allergy_history: Optional[str] = None
    medication_history: Optional[str] = None


class HealthProfileOut(HealthProfileIn):
    user_id: str


class AppointmentIn(BaseModel):
    user_id: str
    department: str
    doctor: str
    doctor_title: Optional[str] = None
    visit_date: date
    period: str
    time_slot: str


class AppointmentOut(AppointmentIn):
    id: int
    no: str = ""          # 规格书 6.1：展示为 YL + 6 位
    status: str = "已预约"


class AppointmentCreateOut(BaseModel):
    """规格书 3.6 输出：{ok, appointment_id, appointments}，重复提交返回既有 ID（幂等）。"""
    ok: bool = True
    appointment_id: int
    created: bool = True          # False 表示命中幂等去重，返回既有 ID
    appointment: AppointmentOut
    appointments: list = []


class AppointmentSlot(BaseModel):
    time_slot: str
    doctor: str
    doctor_title: str
    quota: int
    booked: int
    remaining: int


class AppointmentPeriodOut(BaseModel):
    period: str                  # 上午 / 下午
    total: int
    booked: int
    remaining: int
    slots: list[AppointmentSlot] = []


class AppointmentDayOut(BaseModel):
    visit_date: str
    weekday: str
    periods: list[AppointmentPeriodOut] = []


class AppointmentScheduleOut(BaseModel):
    department: str
    days: list[AppointmentDayOut] = []


class ReportItem(BaseModel):
    name: str
    value: str
    unit: str = ""
    reference_range: str = ""
    flag: str = "正常"


class ReportOut(BaseModel):
    id: str
    name: str
    department: str
    exam_date: str
    items: list[ReportItem]
    risk_level: str


class ReportInterpretOut(BaseModel):
    id: str
    department: str
    risk_level: str
    analysis: str
    interpretation: str
