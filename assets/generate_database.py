from dataclasses import asdict
import json
from dotenv import load_dotenv
from contracts import get_season_data
import asyncio

load_dotenv()


async def main():
	season, _ = await get_season_data()

	print(season)

	with open("winter_2025.json", "w") as f:
		json.dump(asdict(season), f, indent=4)


asyncio.run(main())
