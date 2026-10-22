from sqlalchemy.orm import Session as DBSession

from model import HealthProfile


def _out(p: HealthProfile) -> dict:
    return {
        "user_id": p.user_id,
        "age": p.age,
        "gender": p.gender,
        "chronic_diseases": p.chronic_diseases,
        "allergy_history": p.allergy_history,
        "medication_history": p.medication_history,
    }


def get_profile(db: DBSession, user_id: str) -> dict | None:
    p = db.get(HealthProfile, user_id)
    return _out(p) if p else None


def upsert_profile(db: DBSession, user_id: str, body: dict) -> dict:
    p = db.get(HealthProfile, user_id)
    if not p:
        p = HealthProfile(user_id=user_id)
        db.add(p)
    for field, value in body.items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return _out(p)
