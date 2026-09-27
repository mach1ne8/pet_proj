import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import SessionLocal
from models import NegotiationSession, ProfileReport, SessionResult
from services.llm.base import ProfileRound
from services.llm.factory import get_llm_provider


logger = logging.getLogger(__name__)
_analysis_semaphore = asyncio.Semaphore(1)
_running_reports: set[uuid.UUID] = set()


async def completed_rounds(db: AsyncSession, session_ids: list[uuid.UUID]) -> list[ProfileRound]:
    rows = (await db.execute(
        select(SessionResult)
        .join(NegotiationSession, SessionResult.session_id == NegotiationSession.id)
        .where(SessionResult.session_id.in_(session_ids), NegotiationSession.status == "completed")
    )).scalars().all()
    by_id = {item.session_id: item for item in rows}
    if len(by_id) != len(session_ids):
        raise ValueError("All selected sessions must be completed and have a result")
    return [
        ProfileRound(
            score=by_id[session_id].final_score,
            skills=by_id[session_id].skills,
            strengths=by_id[session_id].strengths,
            mistakes=by_id[session_id].mistakes,
            recommendations=by_id[session_id].recommendations,
        )
        for session_id in session_ids
    ]


async def generate_profile_report(report_id: uuid.UUID) -> None:
    if report_id in _running_reports:
        return
    _running_reports.add(report_id)
    try:
        async with _analysis_semaphore:
            async with SessionLocal() as db:
                report = await db.get(ProfileReport, report_id)
                if report is None or report.status != "pending":
                    return
                rounds = await completed_rounds(db, [uuid.UUID(value) for value in report.session_ids])

            analysis = await get_llm_provider().analyze_profile(rounds)

            async with SessionLocal() as db:
                report = await db.get(ProfileReport, report_id)
                if report and report.status == "pending":
                    report.analysis = {**analysis.model_dump(), "rounds_analyzed": len(rounds)}
                    report.status = "ready"
                    await db.commit()
    except Exception as error:
        logger.warning("Profile analysis %s failed (%s)", report_id, type(error).__name__)
        async with SessionLocal() as db:
            report = await db.get(ProfileReport, report_id)
            if report and report.status == "pending":
                report.status = "failed"
                await db.commit()
    finally:
        _running_reports.discard(report_id)
