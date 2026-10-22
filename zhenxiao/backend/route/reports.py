from fastapi import APIRouter, HTTPException

from service.report_service import list_reports, interpret_report
from route.schemas import ReportOut, ReportInterpretOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
def _list():
    return list_reports()


@router.get("/{report_id}/interpret", response_model=ReportInterpretOut)
def _interpret(report_id: str):
    data = interpret_report(report_id)
    if not data:
        raise HTTPException(status_code=404, detail="报告不存在")
    return data
