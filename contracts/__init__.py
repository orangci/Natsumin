from contracts.classes import Season, User, Contract, SeasonStats
from contracts.Winter2025 import get_data, DASHBOARD_ROW_NAMES, OPTIONAL_CONTRACTS
from async_lru import alru_cache
import aiohttp
import datetime
import asyncio
import gc

_season_sheet_session: aiohttp.ClientSession | None = None


async def get_season_sheet_session() -> aiohttp.ClientSession:
	global _season_sheet_session
	if _season_sheet_session is None or _season_sheet_session.closed:
		_season_sheet_session = aiohttp.ClientSession(headers={"Accept-Encoding": "gzip, deflate"})
	return _season_sheet_session


@alru_cache(ttl=2.5 * 60, maxsize=1)
async def get_season_data(season: str = "Winter 2025") -> tuple[Season, float]:
	match season:
		case "Winter 2025":
			return await get_data(await get_season_sheet_session()), datetime.datetime.now(datetime.UTC).timestamp()


async def cache_reset_loop():
	while True:
		await asyncio.sleep(2.5 * 60)
		get_season_data.cache_clear()
		gc.collect()
