from contracts.classes import Season, User, Contract, SeasonStats  # noqa: F401
from config import BOT_CONFIG
from async_lru import alru_cache
import contracts.Winter2025 as Winter2025
import contracts.Fall2024 as Fall2024
import aiohttp
import datetime
import asyncio
import gc

AVAILABLE_SEASONS = ["Fall 2024", "Winter 2025"]

_season_sheet_session: aiohttp.ClientSession | None = None


async def get_season_sheet_session() -> aiohttp.ClientSession:
	global _season_sheet_session
	if _season_sheet_session is None or _season_sheet_session.closed:
		_season_sheet_session = aiohttp.ClientSession(headers={"Accept-Encoding": "gzip, deflate"})
	return _season_sheet_session


def get_contract_types(season: str = None) -> list[str]:
	if season is None:
		season = BOT_CONFIG.active_season

	match season:
		case "Winter 2025":
			return Winter2025.CONTRACT_TYPES
		case "Fall 2024":
			return Fall2024.CONTRACT_TYPES


def get_optional_contract_types(season: str = None) -> list[str]:
	if season is None:
		season = BOT_CONFIG.active_season

	match season:
		case "Winter 2025":
			return Winter2025.OPTIONAL_CONTRACTS
		case "Fall 2024":
			return Fall2024.OPTIONAL_CONTRACTS


@alru_cache(ttl=2.5 * 60, maxsize=16)
async def get_season_data(season: str = None) -> tuple[Season, float]:
	if season is None:
		season = BOT_CONFIG.active_season

	session = await get_season_sheet_session()

	season_data: Season
	match season:
		case "Winter 2025":
			season_data = await Winter2025.get_data(session)
		case "Fall 2024":
			season_data = await Fall2024.get_data(session)

	await session.close()
	return season_data, datetime.datetime.now(datetime.UTC).timestamp()


async def cache_reset_loop():
	while True:
		await asyncio.sleep(2.5 * 60)
		get_season_data.cache_clear()
		gc.collect()
