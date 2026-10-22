"""预约挂号：按科室生成未来 7 天排班号源，支持预约（幂等/占号）与取消。

对应规格书 3.6 FR-APPOINTMENT。
"""
import random
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from model import Appointment
from utils import rules

SCHEDULE_DAYS = 7
PERIODS = [("上午", "08:30-12:00"), ("下午", "14:00-17:30")]
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

DOCTORS = [
    ("张建国", "主任医师"),
    ("李慧敏", "副主任医师"),
    ("王海涛", "主治医师"),
    ("陈晓雯", "副主任医师"),
    ("刘志强", "主任医师"),
    ("赵梦琪", "主治医师"),
    ("孙一鸣", "副主任医师"),
    ("周雅静", "主治医师"),
]
SLOT_TEMPLATES = {
    "上午": ["08:30-09:00", "09:00-09:30", "09:30-10:00", "10:00-10:30", "10:30-11:00"],
    "下午": ["14:00-14:30", "14:30-15:00", "15:00-15:30", "15:30-16:00", "16:00-16:30"],
}
SLOT_QUOTA = 6          # 每个时间段的号源总数


def format_no(appointment_id: int) -> str:
    """规格书 6.1：id 展示为 YL + 6 位。"""
    return f"YL{appointment_id:06d}"


def _out(a: Appointment) -> dict:
    return {
        "id": a.id,
        "no": format_no(a.id),
        "user_id": a.user_id,
        "department": a.department,
        "doctor": a.doctor,
        "doctor_title": a.doctor_title,
        "visit_date": a.visit_date.isoformat() if a.visit_date else None,
        "period": a.period,
        "time_slot": a.time_slot,
        "status": a.status,
    }


def _booked_slots(db: DBSession, department: str) -> dict:
    """该科室已预约记录 → {(visit_date, period, time_slot): 已约数}。"""
    rows = (
        db.query(Appointment)
        .filter(Appointment.department == department, Appointment.status == "已预约")
        .all()
    )
    booked: dict = {}
    for a in rows:
        key = (a.visit_date.isoformat() if a.visit_date else "", a.period, a.time_slot)
        booked[key] = booked.get(key, 0) + 1
    return booked


def schedule_for_department(
    db: DBSession,
    department: str,
    user_id: str | None = None,
    start: date | None = None,
) -> dict:
    """按科室生成未来 7 天 × 上午/下午排班。

    规格书 3.6：以科室名做随机种子，保证同一科室结果稳定可复现；
    剩余号源 = 总数 − 已预约数，实时扣减。
    """
    department = (department or "").strip()
    if not department:
        raise HTTPException(status_code=400, detail="缺少科室参数")
    if department not in rules.DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f"科室不在系统科室列表中：{department}")

    rnd = random.Random(department)          # 固定种子 → 同科室结果稳定
    start = start or date.today()
    booked = _booked_slots(db, department)

    days = []
    for offset in range(SCHEDULE_DAYS):
        d = start + timedelta(days=offset)
        periods = []
        for period, _ in PERIODS:
            slots = []
            p_total = p_booked = 0
            for tpl in SLOT_TEMPLATES[period]:
                doctor, title = DOCTORS[rnd.randrange(len(DOCTORS))]
                quota = SLOT_QUOTA
                key = (d.isoformat(), period, tpl)
                used = booked.get(key, 0)
                remaining = max(quota - used, 0)
                p_total += quota
                p_booked += used
                slots.append({
                    "time_slot": tpl,
                    "doctor": doctor,
                    "doctor_title": title,
                    "quota": quota,
                    "booked": used,
                    "remaining": remaining,
                })
            periods.append({
                "period": period,
                "total": p_total,
                "booked": p_booked,
                "remaining": max(p_total - p_booked, 0),
                "slots": slots,
            })
        days.append({
            "visit_date": d.isoformat(),
            "weekday": WEEKDAYS[d.weekday()],
            "periods": periods,
        })

    return {"department": department, "days": days}


def _validate_slot(department: str, visit_date: date, period: str, time_slot: str) -> None:
    start = date.today()
    if visit_date < start or visit_date > start + timedelta(days=SCHEDULE_DAYS - 1):
        raise HTTPException(status_code=400, detail="就诊日期超出未来 7 天可预约范围")
    if period not in dict(PERIODS):
        raise HTTPException(status_code=400, detail="时段只能为上午或下午")
    if time_slot not in SLOT_TEMPLATES.get(period, []):
        raise HTTPException(status_code=400, detail=f"时间段不在{period}排班内：{time_slot}")


def list_appointments(db: DBSession, user_id: str | None = None) -> list:
    q = db.query(Appointment)
    if user_id:
        q = q.filter(Appointment.user_id == user_id)
    return [_out(a) for a in q.order_by(Appointment.created_at.desc()).all()]


def create_appointment(db: DBSession, body: dict) -> dict:
    """创建预约。

    规格书 3.6：remaining<=0 → 400「当前号源已约满」；
    相同（科室+医生+日期+时段）的“已预约”记录去重，重复提交返回既有 ID（幂等）。
    """
    visit_date = body.get("visit_date")
    if isinstance(visit_date, str):
        visit_date = date.fromisoformat(visit_date)
    department = body["department"]
    period = body["period"]
    time_slot = body["time_slot"]
    doctor = body.get("doctor") or ""

    _validate_slot(department, visit_date, period, time_slot)

    user_id = body.get("user_id")

    # 规格书 3.6：对相同（科室+医生+日期+时段）的“已预约”记录做去重，
    # 重复提交返回既有 ID（幂等）。仅对同一用户生效，避免把别人的预约返回给他。
    q = db.query(Appointment).filter(
        Appointment.department == department,
        Appointment.doctor == doctor,
        Appointment.visit_date == visit_date,
        Appointment.period == period,
        Appointment.time_slot == time_slot,
        Appointment.status == "已预约",
    )
    if user_id:
        q = q.filter(Appointment.user_id == user_id)
    existing = q.first()
    if existing:
        return {
            "ok": True,
            "appointment_id": existing.id,
            "created": False,
            "appointment": _out(existing),
            "appointments": list_appointments(db, user_id),
        }

    # 规格书 3.6：remaining<=0 时返回 400「当前号源已约满」
    booked = _booked_slots(db, department)
    used = booked.get((visit_date.isoformat(), period, time_slot), 0)
    if used >= SLOT_QUOTA:
        raise HTTPException(status_code=400, detail="当前号源已约满")

    a = Appointment(
        user_id=body["user_id"],
        department=department,
        doctor=doctor,
        doctor_title=body.get("doctor_title"),
        visit_date=visit_date,
        period=period,
        time_slot=time_slot,
        status="已预约",
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {
        "ok": True,
        "appointment_id": a.id,
        "created": True,
        "appointment": _out(a),
        "appointments": list_appointments(db, a.user_id),
    }


def cancel_appointment(db: DBSession, appointment_id: int, user_id: str | None = None) -> dict:
    """规格书 3.6：取消仅对 status='已预约' 的记录生效。"""
    a = db.get(Appointment, appointment_id)
    if not a or (user_id and a.user_id != user_id):
        raise HTTPException(status_code=404, detail="预约不存在")
    if a.status != "已预约":
        raise HTTPException(status_code=400, detail="该预约已取消，无法重复取消")
    a.status = "已取消"
    db.commit()
    db.refresh(a)
    return {
        "ok": True,
        "appointment_id": a.id,
        "status": a.status,
        "appointment": _out(a),
    }
