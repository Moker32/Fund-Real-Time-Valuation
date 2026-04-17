from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.db.database import DatabaseManager

router = APIRouter(prefix="/api/holidays", tags=["Holidays"])


class HolidayResponse(BaseModel):
    id: int
    market: str
    holiday_date: str
    holiday_name: str | None = None


def get_db() -> DatabaseManager:
    """获取数据库管理器实例（通过依赖注入）"""
    from ..dependencies import get_database_source as get_db_source

    return get_db_source()


@router.get("", response_model=list[HolidayResponse], summary="获取节假日列表")
async def get_holidays(
    market: str | None = Query(None, description="市场标识"),
    year: int | None = Query(None, description="年份"),
) -> list[dict[str, Any]]:
    dao = get_db().holiday_dao
    holidays = dao.get_holidays(market=market, year=year, active_only=True)
    return [
        {
            "id": h.id,
            "market": h.market,
            "holiday_date": h.holiday_date,
            "holiday_name": h.holiday_name,
        }
        for h in holidays
    ]


@router.get("/{market}", response_model=list[HolidayResponse], summary="获取指定市场节假日")
async def get_holidays_by_market(
    market: str,
    year: int | None = Query(None, description="年份"),
) -> list[dict[str, Any]]:
    dao = get_db().holiday_dao
    holidays = dao.get_holidays(market=market, year=year, active_only=True)
    return [
        {
            "id": h.id,
            "market": h.market,
            "holiday_date": h.holiday_date,
            "holiday_name": h.holiday_name,
        }
        for h in holidays
    ]
