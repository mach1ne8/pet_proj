import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models import ProfileReport
from schemas import CreateProfileReportRequest, ProfileReportResponse
from services.profile_reports import completed_rounds, generate_profile_report


router = APIRouter(prefix="/api/profile-reports", tags=["profile"])


def public_report(report: ProfileReport) -> ProfileReportResponse:
    return ProfileReportResponse(report_id=report.id, status=report.status, analysis=report.analysis)


@router.post("", response_model=ProfileReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_profile_report(
    request: CreateProfileReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    ids = list(dict.fromkeys(request.session_ids))
    try:
        await completed_rounds(db, ids)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    report = ProfileReport(session_ids=[str(item) for item in ids], status="pending")
    db.add(report)
    await db.commit()
    await db.refresh(report)
    background_tasks.add_task(generate_profile_report, report.id)
    return public_report(report)


@router.get("/{report_id}", response_model=ProfileReportResponse)
async def get_profile_report(
    report_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(ProfileReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Profile report not found")
    if report.status == "pending":
        background_tasks.add_task(generate_profile_report, report.id)
    return public_report(report)
