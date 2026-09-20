from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from repositories.scenarios import list_scenarios
from schemas import ScenarioSummary


router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioSummary])
async def get_scenarios(
    db: AsyncSession = Depends(get_db),
):
    scenarios = await list_scenarios(db)

    return [
        ScenarioSummary(
            id=scenario.id,
            slug=scenario.slug,
            name=scenario.name,
            description=scenario.description,
            character_name=scenario.character_name,
            character_role=scenario.character_role,
            difficulty=scenario.difficulty,
        )
        for scenario in scenarios
    ]
