import time
from .classes import SeasonDB
from .seasons import Winter2025
from .classes import *  # noqa: F403
from config import BOT_CONFIG

AVAILABLE_SEASONS = ["Winter 2025"]


async def get_season_db(season: str = BOT_CONFIG.active_season) -> SeasonDB:
	if season not in AVAILABLE_SEASONS:
		raise ValueError(f"Invalid season: {season}")

	match season:
		case "Winter 2025":
			return await Winter2025.get_database()


async def sync_season_db(season: str = BOT_CONFIG.active_season) -> float:  # Returns duration of sync
	if season not in AVAILABLE_SEASONS:
		raise ValueError(f"Invalid season: {season}")

	db = await get_season_db(season)
	start = time.perf_counter()

	match season:
		case "Winter 2025":
			await Winter2025.sync_to_latest(db)

	return time.perf_counter() - start
