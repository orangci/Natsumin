import os
import discord
import requests
import datetime
import math
from globals import *
from mezmorize import Cache
from discord.ext import commands
from discord.commands import slash_command

SPREADSHEET_ID = "19aueoNx6BBU6amX7DhKGU8kHVauHWcSGiGKMzFSGkGc"
GET_SHEET_DATA_URL = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/Dashboard!A2%3AU394"

cache = Cache(CACHE_TYPE='filesystem', CACHE_DIR='cache', CACHE_DEFAULT_TIMEOUT=6 * 60 * 60)

ROW_NAMES = {
	0: "Base Contract",
	1: "Challenge Contract",
	2: "Veteran Special",
	3: "Movie Special",
	4: "VN Special",
	5: "Indie Special",
	6: "Extreme Special",
	7: "Base Buddy",
	8: "Challenge Buddy"
}

def get_percentage(num: float, total: float) -> int:
	return math.floor(100 * float(num)/float(total))

def convert_sheet_to_database(sheet_data) -> ContractsDatabase:
	rows: list[list[str]] = sheet_data['values']

	final_data = {
		"users": {}
	}
	total_contracts = 0
	total_contracts_passed = 0
	users_passed = 0
	per_contract_stats: dict[str, list[int]] = {
		"Base Contract": [0, 0],
		"Challenge Contract": [0, 0],
		"Veteran Special": [0, 0],
		"Movie Special": [0, 0],
		"VN Special": [0, 0],
		"Indie Special": [0, 0],
		"Extreme Special": [0, 0],
		"Base Buddy": [0, 0],
		"Challenge Buddy": [0, 0]
	}

	for row in rows:
		status = row[0]
		username = row[1]
		contract_names = row[2:11]
		contract_passed = row[12:21]

		contracts = {}

		for i in range(len(contract_names)):
			row_name = ROW_NAMES[i]
			row_content = contract_names[i]

			if row_content == "-":
				continue

			total_contracts += 1
			per_contract_stats[row_name][1] += 1
			passed_contract = True if len(contract_passed) > i and contract_passed[i] == "PASSED" else False
			if passed_contract:
				total_contracts_passed += 1
				per_contract_stats[row_name][0] += 1

			contracts[row_name] = {"name": row_content, "passed": passed_contract}

		user_passed_contracts = True if status == "P" else False
		if user_passed_contracts:
			users_passed += 1

		final_data["users"][username.lower()] = {
			"status": "PASSED" if status == "P" else "FAILED" if status == "F" else status,
			"contracts": contracts
		}
	
	final_data["stats"] = {
		"users": len(final_data["users"]),
		"users_passed": users_passed,
		"contracts": total_contracts,
		"contracts_passed": total_contracts_passed,
		"contract_types": per_contract_stats
	}
	
	return final_data

@cache.memoize()
def _get_sheet_data_and_update() -> tuple[ContractsDatabase, float]:
	response = requests.get(GET_SHEET_DATA_URL, {
		"majorDimension": "ROWS",
		"valueRenderOption": "FORMATTED_VALUE",
		"key": os.getenv("GOOGLE_API_KEY")
	})

	if response.status_code == 200:
		return convert_sheet_to_database(response.json()), datetime.datetime.now(datetime.UTC).timestamp()
	else:
		print("RESPONSE FAILED:", response.status_code, response.json())

class Contracts(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot

	contracts_group: discord.SlashCommandGroup = discord.SlashCommandGroup(
		guild_ids=config["debug_servers"], 
		name="contracts", 
		description="Contracts related commands",
	)

	@contracts_group.command(name="get", description="See your's or someone else's contracts")
	async def get(
		self, 
		ctx: discord.ApplicationContext, 
		user: discord.Option(discord.User, description="User to check contract's of", required=False), # type: ignore
		is_ephemeral: discord.Option(bool, name="hidden", description="Whether you want the response only visible to you", default=False) # type: ignore
		):
		if user is None:
			user = ctx.author

		contract_database, last_updated_timestamp = _get_sheet_data_and_update()
		contract_user = contract_database["users"].get(user.name, None)
		if not contract_user:
			not_found_embed = discord.Embed(title="Contracts", color=discord.Color.red(), description="User not found! If this is a mistake please ping <@546659584727580692>")
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return

		contracts_passed = 0
		contracts_embed = discord.Embed(color=NATSUMIN_EMBED_COLOR)
		contracts_embed.set_author(name=f"{user.name}{f" [{contract_user["status"]}]" if contract_user["status"].strip() != "" else ""}", icon_url=user.display_avatar.url)
		last_updated_datetime = datetime.datetime.fromtimestamp(last_updated_timestamp)
		contracts_embed.set_footer(text=f"Database last updated on {last_updated_datetime.strftime("%d/%m/%Y, %H:%M")} UTC", icon_url="https://cdn.discordapp.com/emojis/998705274074435584.webp?size=4096")
		for contract_type in contract_user["contracts"]:
			contract_data = contract_user["contracts"][contract_type]
			contract_name = contract_data["name"]
			if contract_name == "-":
				continue
			elif contract_name == "PLEASE SELECT":
				contract_name = f"__**{contract_name}**__"

			if contract_data["passed"] == True:
				contracts_passed += 1

			contracts_embed.add_field(name=f"{contract_type} {"✅" if contract_data["passed"] else "❌"}", value=contract_name, inline=True)
		contracts_embed.title = f"Contracts ({contracts_passed}/{len(contract_user["contracts"].keys())})"
		

		await ctx.respond(embed=contracts_embed, ephemeral=is_ephemeral)

	@contracts_group.command(name="stats", description="Check the season's stats")
	async def stats(
		self, 
		ctx: discord.ApplicationContext, 
		is_ephemeral: discord.Option(bool, name="hidden", description="Whether you want the response only visible to you", default=False) # type: ignore
	):
		contract_database, last_updated_timestamp = _get_sheet_data_and_update()
		season_stats = contract_database["stats"]
		embed = discord.Embed(title="Contracts Winter 2025", color=NATSUMIN_EMBED_COLOR)
		embed.description = (
			f"Users passed: {season_stats["users_passed"]}/{season_stats["users"]} ({get_percentage(season_stats["users_passed"],season_stats["users"])}%)\n" +
			f"Contracts passed: {season_stats["contracts_passed"]}/{season_stats["contracts"]} ({get_percentage(season_stats["contracts_passed"],season_stats["contracts"])}%)"
		)
		last_updated_datetime = datetime.datetime.fromtimestamp(last_updated_timestamp)
		embed.set_footer(text=f"Database last updated on {last_updated_datetime.strftime("%d/%m/%Y, %H:%M")} UTC", icon_url="https://cdn.discordapp.com/emojis/998705274074435584.webp?size=4096")
		for contract_type in season_stats["contract_types"]:
			type_stats = season_stats["contract_types"][contract_type]
			embed.add_field(name=f"{contract_type} ({get_percentage(type_stats[0], type_stats[1])}%)", value=f"{type_stats[0]}/{type_stats[1]}")
		
		await ctx.respond(embed=embed, ephemeral=is_ephemeral)

	@commands.command()
	@commands.is_owner()
	async def get_database(self, ctx: commands.Context):
		contract_database, _ = _get_sheet_data_and_update()
		with open("database.json", "w") as f:
			json.dump(contract_database, f, indent=4)
		await ctx.reply("Database now uploaded at ``database.json``",delete_after=3)

	@commands.command()
	@commands.is_owner()
	async def purge_cache(self, ctx: commands.Context):
		cache.clear()
		await ctx.reply("Cache purged!! Next command will request updated data.",delete_after=3)

def setup(bot:commands.Bot):
	bot.add_cog(Contracts(bot))