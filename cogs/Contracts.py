import os
import discord
import requests
import datetime
from globals import *
from mezmorize import Cache
from discord.ext import commands
from discord.commands import slash_command

SPREADSHEET_ID = "19aueoNx6BBU6amX7DhKGU8kHVauHWcSGiGKMzFSGkGc"
GET_SHEET_DATA_URL = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/Dashboard!A2%3AU394"

cache = Cache(CACHE_TYPE='filesystem', CACHE_DIR='cache', CACHE_DEFAULT_TIMEOUT=24 * 60 * 60)

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

def convert_sheet_to_database(sheet_data) -> dict:
	rows: list[list[str]] = sheet_data['values']

	final_data = {}

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
			passed_contract = True if len(contract_passed) > i and contract_passed[i] == "PASSED" else False
			contracts[row_name] = {"name": row_content, "passed": passed_contract}


		final_data[username.lower()] = {
			"status": "PASSED" if status == "P" else "FAILED" if status == "F" else status,
			"contracts": contracts
		}
	
	return final_data

@cache.memoize()
def _get_sheet_data_and_update() -> tuple[dict[str, ContractsUser], float]:
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

	@slash_command(guild_ids=config["debug_servers"], name="contracts", description="See your's or someone else's contracts")
	async def contracts(
		self, 
		ctx: discord.ApplicationContext, 
		user: discord.Option(discord.User, description="User to check contract's of", required=False), # type: ignore
		is_ephemeral: discord.Option(bool, name="ephemeral", description="If the response is only visible to you", default=False) # type: ignore
		):
		"""
		if not await self.bot.is_owner(ctx.author):
			await ctx.respond("i am testing go away -richard", ephemeral=True)
			return
		"""

		if user is None:
			user = ctx.author

		contract_database, last_updated_timestamp = _get_sheet_data_and_update()
		contract_user = contract_database.get(user.name, None)
		if not contract_user:
			not_found_embed = discord.Embed(title="Contracts", color=discord.Color.red(), description="User not found! If this is a mistake please ping <@546659584727580692>")
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return
		
		contracts_embed = discord.Embed(title="Contracts", color=NATSUMIN_EMBED_COLOR)
		contracts_embed.set_author(name=f"{user.name}", icon_url=user.display_avatar.url)
		last_updated_datetime = datetime.datetime.fromtimestamp(last_updated_timestamp)
		contracts_embed.set_footer(text=f"Database last updated on {last_updated_datetime.strftime("%d/%m/%Y, %H:%M")} UTC")
		for contract_type in contract_user["contracts"]:
			contract_data = contract_user["contracts"][contract_type]
			contract_name = contract_data["name"]
			if contract_name == "-":
				continue
			elif contract_name == "PLEASE SELECT":
				contract_name = f"**{contract_name}**"

			contracts_embed.add_field(name=f"{contract_type} {"✅" if contract_data["passed"] else "❌"}", value=contract_name, inline=True)
		
		await ctx.respond(embed=contracts_embed, ephemeral=is_ephemeral)

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