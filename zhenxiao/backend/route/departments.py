"""规格书 3.1 / 附录 A：系统核心科室列表（前端以醒目渐变卡片展示）。"""
from fastapi import APIRouter

from utils import rules

router = APIRouter(prefix="/api", tags=["departments"])


@router.get("/departments")
def _departments():
    return {
        "departments": [
            {"name": name, "index": i + 1} for i, name in enumerate(rules.DEPARTMENTS)
        ],
        "count": len(rules.DEPARTMENTS),
        "medication_department": rules.MEDICATION_DEPARTMENT,
    }
