"""规格书 3.6 / 4.2：科室排班、创建预约（幂等/占号）、我的预约、取消预约。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from model import get_db
from service.appointment_service import (
    list_appointments,
    create_appointment,
    cancel_appointment,
    schedule_for_department,
)
from route.schemas import (
    AppointmentIn,
    AppointmentOut,
    AppointmentCreateOut,
    AppointmentScheduleOut,
)

router = APIRouter(prefix="/api", tags=["appointments"])


@router.get("/appointments")
def _list(user_id: str | None = None, db: DBSession = Depends(get_db)):
    """我的预约。"""
    return {"appointments": list_appointments(db, user_id)}


@router.get("/appointments/schedule", response_model=AppointmentScheduleOut)
def _schedule(
    department: str = Query(..., description="科室名，如 呼吸科"),
    user_id: str | None = None,
    db: DBSession = Depends(get_db),
):
    """科室未来 7 天上午/下午排班号源（同科室结果稳定可复现）。"""
    return schedule_for_department(db, department, user_id)


@router.post("/appointments", response_model=AppointmentCreateOut)
def _create(body: AppointmentIn, db: DBSession = Depends(get_db)):
    """创建预约。剩余号源为 0 → 400「当前号源已约满」；重复提交返回既有 ID。"""
    return create_appointment(db, body.model_dump())


@router.delete("/appointments/{appointment_id}")
def _cancel(
    appointment_id: int,
    user_id: str | None = None,
    db: DBSession = Depends(get_db),
):
    """取消预约，仅对 status='已预约' 的记录生效。"""
    return cancel_appointment(db, appointment_id, user_id)
