import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Scenario


DEFAULT_SCENARIO_SLUG = "supplier-procurement"


async def get_scenario(
    db: AsyncSession,
    scenario_id: uuid.UUID,
) -> Scenario | None:
    result = await db.execute(
        select(Scenario).where(Scenario.id == scenario_id)
    )
    return result.scalar_one_or_none()


async def get_default_scenario(
    db: AsyncSession,
) -> Scenario | None:
    result = await db.execute(
        select(Scenario).where(
            Scenario.slug == DEFAULT_SCENARIO_SLUG
        )
    )
    return result.scalar_one_or_none()


async def list_scenarios(
    db: AsyncSession,
) -> list[Scenario]:
    result = await db.execute(
        select(Scenario).order_by(Scenario.name)
    )
    return list(result.scalars().all())
