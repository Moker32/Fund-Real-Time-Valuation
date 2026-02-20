from datetime import date
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.db.database import DatabaseManager, ExchangeHoliday

router = APIRouter(prefix="/api/holidays", tags=["Holidays"])


class HolidayRequest(BaseModel):
    market: str
    holiday_date: str
    holiday_name: str | None = None


class HolidayResponse(BaseModel):
    id: int
    market: str
    holiday_date: str
    holiday_name: str | None = None
    is_active: bool


class BatchHolidayRequest(BaseModel):
    holidays: list[HolidayRequest]


_db: DatabaseManager | None = None


def get_db() -> DatabaseManager:
    global _db
    if _db is None:
        _db = DatabaseManager()
    return _db


@router.get("", response_model=list[HolidayResponse], summary="获取节假日列表")
async def get_holidays(
    market: str | None = Query(None, description="市场标识"),
    year: int | None = Query(None, description="年份"),
    include_inactive: bool = Query(False, description="包含已删除的节假日"),
) -> list[dict[str, Any]]:
    dao = get_db().holiday_dao
    holidays = dao.get_holidays(market=market, year=year, active_only=not include_inactive)
    return [
        {
            "id": h.id,
            "market": h.market,
            "holiday_date": h.holiday_date,
            "holiday_name": h.holiday_name,
            "is_active": bool(h.is_active),
        }
        for h in holidays
    ]


@router.get("/{market}", response_model=list[HolidayResponse], summary="获取指定市场节假日")
async def get_holidays_by_market(
    market: str,
    year: int | None = Query(None, description="年份"),
    include_inactive: bool = Query(False, description="包含已删除的节假日"),
) -> list[dict[str, Any]]:
    dao = get_db().holiday_dao
    holidays = dao.get_holidays(market=market, year=year, active_only=not include_inactive)
    return [
        {
            "id": h.id,
            "market": h.market,
            "holiday_date": h.holiday_date,
            "holiday_name": h.holiday_name,
            "is_active": bool(h.is_active),
        }
        for h in holidays
    ]


@router.post("", response_model=dict, summary="添加节假日")
async def add_holiday(request: HolidayRequest) -> dict:
    dao = get_db().holiday_dao
    success = dao.add_holiday(
        market=request.market,
        holiday_date=request.holiday_date,
        holiday_name=request.holiday_name,
    )
    return {"success": success, "message": "节假日添加成功" if success else "节假日添加失败"}


@router.post("/batch", response_model=dict, summary="批量导入节假日")
async def batch_add_holidays(request: BatchHolidayRequest) -> dict:
    dao = get_db().holiday_dao
    holidays = [
        ExchangeHoliday(
            market=h.market,
            holiday_date=h.holiday_date,
            holiday_name=h.holiday_name,
        )
        for h in request.holidays
    ]
    count = dao.add_holidays(holidays)
    return {"success": True, "count": count, "message": f"成功导入 {count} 条节假日"}


@router.delete("/{holiday_id}", response_model=dict, summary="软删除节假日")
async def delete_holiday(holiday_id: int) -> dict:
    dao = get_db().holiday_dao
    success = dao.soft_delete(holiday_id)
    return {"success": success, "message": "节假日已删除（软删除）" if success else "节假日不存在"}


@router.post("/{holiday_id}/restore", response_model=dict, summary="恢复节假日")
async def restore_holiday(holiday_id: int) -> dict:
    dao = get_db().holiday_dao
    success = dao.restore(holiday_id)
    return {"success": success, "message": "节假日已恢复" if success else "节假日不存在"}


@router.delete("/{holiday_id}/hard", response_model=dict, summary="永久删除节假日")
async def hard_delete_holiday(holiday_id: int) -> dict:
    dao = get_db().holiday_dao
    success = dao.delete(holiday_id)
    return {"success": success, "message": "节假日已永久删除" if success else "节假日不存在"}


@router.post("/import-from-code", response_model=dict, summary="从代码导入硬编码节假日")
async def import_holidays_from_code() -> dict:
    return {"success": True, "count": 0, "message": "数据已存储在数据库中，无需重复导入"}


@router.post("/populate-world-holidays", response_model=dict, summary="预填充全球市场节假日")
async def populate_world_holidays(years: list[int] = Query([2025, 2026, 2027])) -> dict:
    from holidays import CountryHoliday

    dao = get_db().holiday_dao
    count = 0
    markets = {
        "usa": ("US", ["US"]),
        "hk": ("HK", ["HK"]),
        "japan": ("JP", ["JP"]),
        "uk": ("GB", ["UK"]),
        "germany": ("DE", ["DE"]),
        "france": ("FR", ["FR"]),
    }

    for market_id, (country_code, _) in markets.items():
        for year in years:
            try:
                holidays = CountryHoliday(country_code, years=year)
                for holiday_date, holiday_name in holidays.items():
                    dao.add_holiday(market_id, holiday_date.isoformat(), holiday_name)
                    count += 1
            except Exception:
                pass

    return {"success": True, "count": count, "message": f"成功导入 {count} 条全球节假日"}
