import os
import discord
import requests
import datetime
import math
from globals import *
from contracts_database import *
from typing import Optional
from mezmorize import Cache
from discord.ext import commands
from discord.commands import slash_command

SPREADSHEET_ID = "19aueoNx6BBU6amX7DhKGU8kHVauHWcSGiGKMzFSGkGc"
GET_SHEET_DATA_URL = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values:batchGet"

SHEET_DATA_CACHE_HOURS = 6
SHEET_DATA_CACHE_DURATION = SHEET_DATA_CACHE_HOURS * 60 * 60

cache = Cache(CACHE_TYPE='filesystem', CACHE_DIR='cache', CACHE_DEFAULT_TIMEOUT=1 * 60 * 60)

def get_percentage(num: float, total: float) -> int:
	return math.floor(100 * float(num)/float(total))

def _get_member_from_username(bot: commands.Bot, username: str) -> Optional[int]:
	"""Get the user ID from the username"""
	for member in bot.get_all_members():
		if member.name.lower() == username.lower():
			return member
	return None

async def get_contract_usernames(ctx: discord.AutocompleteContext): 
	contracts_database, _ = _get_sheet_data_and_update()
	matching: list[str] = [username.lower() for username in contracts_database["users"].keys() if ctx.value.strip().lower() in username.lower()]
	return matching

@cache.memoize(timeout=SHEET_DATA_CACHE_DURATION)
def _get_sheet_data_and_update() -> tuple[ContractsDatabase, float]:
	response = requests.get(GET_SHEET_DATA_URL, {
		"majorDimension": "ROWS",
		"valueRenderOption": "FORMATTED_VALUE",
		"ranges": [
			"Dashboard!A2:U394",
			"Base!A2:AG394",
			"Veteran Special!A2:I167",
			"VN Special!A2:G126",
			"Movie Special!A2:H243",
			"Indie Special!A2:H136",
			"Extreme Special!A2:G95",
			"Buddying!B2:N68"
		],
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
		username: discord.Option(str, name="username", description="User to check", required=False, autocomplete=get_contract_usernames), # type: ignore
		is_ephemeral: discord.Option(bool, name="hidden", description="Whether you want the response only visible to you", default=False) # type: ignore
		):
		user: discord.Member = None
		if username is None:
			user = ctx.author
			username = ctx.author.name
		else:
			user = _get_member_from_username(self.bot, username)

		contract_database, last_updated_timestamp = _get_sheet_data_and_update()
		contract_user = contract_database["users"].get(username, None)
		if not contract_user:
			not_found_embed = discord.Embed(title="Contracts", color=discord.Color.red(), description="User not found! If this is a mistake please ping <@546659584727580692>")
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return

		contracts_passed = 0
		contracts_embed = discord.Embed(color=NATSUMIN_EMBED_COLOR)
		contracts_embed.set_author(
			name=f"{username}{f" [{contract_user["status"]}]" if contract_user["status"].strip() != "" else ""}",
			icon_url=user.display_avatar.url if user else None,
			url=contract_user["list_url"] if contract_user["list_url"] != "" else None
		)
		last_updated_datetime = datetime.datetime.fromtimestamp(last_updated_timestamp, datetime.UTC)
		next_update_datetime = last_updated_datetime + datetime.timedelta(hours=SHEET_DATA_CACHE_HOURS)
		current_datetime = datetime.datetime.now(datetime.UTC)
		difference = next_update_datetime - current_datetime
		difference_seconds = max(difference.total_seconds(), 0)
		hours, remainder = divmod(difference_seconds, 3600)
		minutes, seconds = divmod(remainder, 60)
		contracts_embed.set_footer(
			text=f"Data updating in {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}",
			icon_url="https://cdn.discordapp.com/emojis/998705274074435584.webp?size=4096"
		)
		for contract_type in contract_user["contracts"]:
			contract_data = contract_user["contracts"][contract_type]
			contract_name = contract_data["name"]
			field_symbol = "✅" if contract_data["passed"] else "❌"
			if contract_name == "-":
				continue
			elif contract_name == "PLEASE SELECT":
				contract_name = f"__**{contract_name}**__"
				field_symbol = "⚠️"

			if contract_data["passed"] == True:
				contracts_passed += 1

			contracts_embed.add_field(name=f"{contract_type} {field_symbol}", value=contract_name, inline=True)
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
			f"Season ending on **<t:1746943200:D>** at **<t:1746943200:t>**\n" +
			f"Users passed: {season_stats["users_passed"]}/{season_stats["users"]} ({get_percentage(season_stats["users_passed"],season_stats["users"])}%)\n" +
			f"Contracts passed: {season_stats["contracts_passed"]}/{season_stats["contracts"]} ({get_percentage(season_stats["contracts_passed"],season_stats["contracts"])}%)"
		)
		last_updated_datetime = datetime.datetime.fromtimestamp(last_updated_timestamp, datetime.UTC)
		next_update_datetime = last_updated_datetime + datetime.timedelta(hours=SHEET_DATA_CACHE_HOURS)
		current_datetime = datetime.datetime.now(datetime.UTC)
		difference = next_update_datetime - current_datetime
		difference_seconds = max(difference.total_seconds(), 0)
		hours, remainder = divmod(difference_seconds, 3600)
		minutes, seconds = divmod(remainder, 60)
		embed.set_footer(
			text=f"Data updating in {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}",
			icon_url="https://cdn.discordapp.com/emojis/998705274074435584.webp?size=4096"
		)
		for contract_type in season_stats["contract_types"]:
			type_stats = season_stats["contract_types"][contract_type]
			embed.add_field(name=f"{contract_type} ({get_percentage(type_stats[0], type_stats[1])}%)", value=f"{type_stats[0]}/{type_stats[1]}")
		
		await ctx.respond(embed=embed, ephemeral=is_ephemeral)

	@contracts_group.command(name="user", description="Get contracts user info")
	async def user(
		self, 
		ctx: discord.ApplicationContext, 
		username: discord.Option(str, name="username", description="User to check", required=False, autocomplete=get_contract_usernames), # type: ignore
		is_ephemeral: discord.Option(bool, name="hidden", description="Whether you want the response only visible to you", default=False) # type: ignore
	):
		user: discord.Member = None
		if username is None:
			user = ctx.author
			username = ctx.author.name
		else:
			user = _get_member_from_username(self.bot, username)
	
		contract_database, last_updated_timestamp = _get_sheet_data_and_update()
		contract_user = contract_database["users"].get(username, None)
		if not contract_user:
			not_found_embed = discord.Embed(title="User Info", color=discord.Color.red(), description="User not found! If this is a mistake please ping <@546659584727580692>")
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return

		contracts_embed = discord.Embed(color=NATSUMIN_EMBED_COLOR)
		contracts_embed.set_author(
			name=f"{username}{f" [{contract_user["status"]}]" if contract_user["status"].strip() != "" else ""}",
			icon_url=user.display_avatar.url if user else None,
			url=contract_user["list_url"] if contract_user["list_url"] != "" else None
		)
		last_updated_datetime = datetime.datetime.fromtimestamp(last_updated_timestamp, datetime.UTC)
		next_update_datetime = last_updated_datetime + datetime.timedelta(hours=SHEET_DATA_CACHE_HOURS)
		current_datetime = datetime.datetime.now(datetime.UTC)
		difference = next_update_datetime - current_datetime
		difference_seconds = max(difference.total_seconds(), 0)
		hours, remainder = divmod(difference_seconds, 3600)
		minutes, seconds = divmod(remainder, 60)
		contracts_embed.set_footer(
			text=f"Data updating in {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}",
			icon_url="https://cdn.discordapp.com/emojis/998705274074435584.webp?size=4096"
		)

		contracts_embed.description = (
			f"**Rep**: {contract_user["rep"]}\n" +
			f"**Contractor**: {contract_user["contractor"]}\n" +
			(f"**List**: {contract_user["list_url"]}" if contract_user["list_url"] != "" else "")
		)
		contracts_embed.add_field(name="Preferences", value=contract_user["preferences"], inline=True)
		contracts_embed.add_field(name="Bans", value=contract_user["bans"], inline=True)

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