import datetime
import gc
import logging
import discord
from typing import Optional
import math
import re
from config import (
	BOT_CONFIG,
	BASE_EMBED_COLOR,
	CONSOLE_LOGGING_FORMATTER,
	FILE_LOGGING_FORMATTER,
	DEADLINE_TIMESTAMP,
	DEADLINE_TIMESTAMP_INT,
)
from discord.ext import commands, tasks
import contracts
from contracts import get_season_data, DASHBOARD_ROW_NAMES
from shared import get_member_from_username

contract_categories = {
	"All": [
		"Base Contract",
		"Challenge Contract",
		"Veteran Special",
		"Movie Special",
		"VN Special",
		"Indie Special",
		"Extreme Special",
		"Base Buddy",
		"Challenge Buddy",
	],
	"Primary": ["Base Contract", "Challenge Contract"],
	"Specials": [
		"Veteran Special",
		"Movie Special",
		"VN Special",
		"Indie Special",
		"Extreme Special",
	],
	"Buddies": ["Base Buddy", "Challenge Buddy"],
}


async def _create_user_contracts_embed(
	selected_category: str,
	user: contracts.User,
	sender: discord.Member,
	target: discord.Member,
) -> discord.Embed:
	season, last_updated_timestamp = await get_season_data()
	embed = get_common_embed(last_updated_timestamp, user, target)

	for contract_type in contract_categories.get(selected_category, []):
		contract = user.contracts.get(contract_type)
		if not contract or contract.name == "-":
			continue

		symbol = "✅" if contract.passed else "❌"
		if contract.name == "PLEASE SELECT":
			symbol = "⚠️"
			contract_name = f"__**{contract.name}**__"
		else:
			contract_name = contract.name

		line = f"> {symbol} **{contract_type}**: "
		line += f"[{contract_name}]({contract.review_url})" if contract.review_url else contract_name
		embed.description += "\n" + line

	if user.status == "PASSED":
		embed.description += "\n\n This user has **passed** the season."

	passed = len([c for c in user.contracts.values() if c.passed])
	total = len(user.contracts)
	embed.title = f"Contracts ({passed}/{total})"

	return embed


async def _get_contracts_user_and_member(bot: commands.Bot, ctx_user: discord.Member, username: Optional[str]):
	if not username:
		return ctx_user, ctx_user.name

	match = re.match(r"<@!?(\d+)>", username)
	if match:
		user_id = int(match.group(1))
		member = ctx_user.guild.get_member(user_id) or await bot.get_or_fetch_user(user_id)
		return member, member.name if member else None

	return get_member_from_username(bot, username), username


async def _send_contracts_embed_response(ctx, user: contracts.User, sender, target, ephemeral=False):
	embed = await _create_user_contracts_embed("All", user, sender, target)
	await ctx.respond(embed=embed, ephemeral=ephemeral)


def get_percentage(num: float, total: float) -> int:
	return math.floor(100 * float(num) / float(total))


async def get_contracts_reps(ctx: discord.AutocompleteContext):
	season, _ = await get_season_data()
	return [rep for rep in season.reps if ctx.value.strip().upper() in rep]


async def get_contracts_usernames(ctx: discord.AutocompleteContext):
	season, _ = await get_season_data()
	matching: list[str] = [username.lower() for username in season.users if ctx.value.strip().lower() in username.lower()]
	return matching


def get_common_embed(
	timestamp: float,
	contracts_user: Optional[contracts.User] = None,
	discord_member: Optional[discord.Member] = None,
) -> discord.Embed:
	embed = discord.Embed(color=BASE_EMBED_COLOR, description="")
	if contracts_user:
		# if discord_member:
		# embed.set_thumbnail(url=discord_member.display_avatar.url)
		embed.set_author(
			name=f"{contracts_user.name} {'✅' if contracts_user.status == 'PASSED' else '❌' if contracts_user.status == 'FAILED' else ''}",
			url=contracts_user.list_url if contracts_user.list_url != "" else None,
			icon_url=discord_member.display_avatar.url if discord_member else None,
		)

	current_datetime = datetime.datetime.now(datetime.UTC)
	difference = DEADLINE_TIMESTAMP - current_datetime
	difference_seconds = max(difference.total_seconds(), 0)

	if difference_seconds > 0:
		days, remainder = divmod(difference_seconds, 86400)
		hours, remainder = divmod(remainder, 3600)
		minutes, seconds = divmod(remainder, 60)
		embed.set_footer(
			text=f"Deadline in {int(days)} days, {int(hours)} hours, and {int(minutes)} minutes.",
			icon_url="https://cdn.discordapp.com/emojis/998705274074435584.webp?size=4096",
		)
	else:
		embed.set_footer(
			text="This season has ended.",
			icon_url="https://cdn.discordapp.com/emojis/998705274074435584.webp?size=4096",
		)
	return embed


class Contracts(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.logger = logging.getLogger("bot.contracts")

		if not self.logger.handlers:
			file_handler = logging.FileHandler("logs/contracts.log", encoding="utf-8")
			file_handler.setFormatter(FILE_LOGGING_FORMATTER)
			console_handler = logging.StreamHandler()
			console_handler.setFormatter(CONSOLE_LOGGING_FORMATTER)
			self.logger.addHandler(file_handler)
			self.logger.addHandler(console_handler)

			self.logger.setLevel(logging.INFO)

	def cog_unload(self):
		self.change_user_status.cancel()

	@commands.Cog.listener()
	async def on_ready(self):
		self.change_user_status.start()

	contracts_group = discord.SlashCommandGroup(
		name="contracts",
		description="Contracts related commands",
		guild_ids=BOT_CONFIG.guild_ids,
	)

	# ~~TYPE COMMAND
	@contracts_group.command(name="type", description="Get information regarding a type of contract")
	async def type(
		self,
		ctx: discord.ApplicationContext,
		contract_type: discord.Option(
			str,
			description="Type of contract to check",
			name="type",
			required=True,
			choices=list(DASHBOARD_ROW_NAMES.values()),
		),  # type: ignore
		username: discord.Option(
			str,
			description="User to check",
			required=False,
			autocomplete=get_contracts_usernames,
		),  # type: ignore
		is_ephemeral: discord.Option(
			bool,
			name="hidden",
			description="Whether you want the response only visible to you",
			required=False,
		),  # type: ignore
	):
		selected_member: discord.Member = None
		if username is None:
			selected_member = ctx.author
			username = ctx.author.name
		else:
			selected_member = get_member_from_username(self.bot, username)

		season, last_updated_timestamp = await get_season_data()
		contract_user = season.get_user(username)
		if not contract_user:
			not_found_embed = discord.Embed(
				color=discord.Color.red(),
				description="User not found! If this is a mistake please ping <@546659584727580692>",
			)
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return

		if contract_type not in contract_user.contracts:
			not_found_embed = discord.Embed(
				color=discord.Color.red(),
				description="Contract not found! If this is a mistake please ping <@546659584727580692>",
			)
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return

		contract_data = contract_user.contracts[contract_type]

		contracts_embed = get_common_embed(last_updated_timestamp, contract_user, selected_member)
		contracts_embed.title = contract_type
		contracts_embed.url = contract_data.review_url if contract_data.review_url != "" else None
		contracts_embed.description = (
			f"**Name**: {contract_data.name}\n"
			+ f"**Medium**: {contract_data.medium}\n"
			+ (
				f"**{'Contractor' if contract_data.medium != 'Game' else 'Sponsor'}**: {contract_data.contractor}\n"
				if contract_data.contractor != ""
				else ""
			)
		)
		contract_status = contract_data.status if contract_data.status != "" else "PENDING"
		contracts_embed.add_field(name="Status", value=contract_status.lower().capitalize(), inline=True)
		contracts_embed.add_field(name="Score", value=contract_data.rating, inline=True)
		contracts_embed.add_field(name="Progress", value=contract_data.progress, inline=True)

		await ctx.respond(embed=contracts_embed, ephemeral=is_ephemeral)

	# ~~STATS COMMAND
	async def build_stats_embed(self, rep: Optional[str] = None):
		season, last_updated_timestamp = await get_season_data()

		if rep and rep.upper() not in season.reps:
			return "Invalid rep!"

		if not rep:
			season_stats = season.stats
		else:
			users_passed = users_total = contracts_passed = contracts_total = 0
			contract_types = {}

			for user in season.users.values():
				if user.rep.upper() != rep.upper():
					continue
				users_total += 1
				if user.status == "PASSED":
					users_passed += 1
				for ctype, cdata in user.contracts.items():
					if ctype not in contract_types:
						contract_types[ctype] = [0, 0]
					contract_types[ctype][1] += 1
					if cdata.passed:
						contract_types[ctype][0] += 1
						contracts_passed += 1
				contracts_total += len(user.contracts)

			season_stats = contracts.SeasonStats(
				users_passed=users_passed,
				users=users_total,
				contracts_passed=contracts_passed,
				contracts=contracts_total,
				contract_types=contract_types,
			)

		embed = get_common_embed(last_updated_timestamp)
		embed.title = "Contracts Winter 2025" if not rep else f"Contracts Winter 2025 - {rep.upper()} [{season.reps[rep.upper()]}]"
		embed.description = ""

		if not rep:
			embed.description += f"\nSeason ending on **<t:{DEADLINE_TIMESTAMP_INT}:D>** at **<t:{DEADLINE_TIMESTAMP_INT}:t>**."

		embed.description += (
			f"\n> **Users passed**: {season_stats.users_passed}/{season_stats.users} "
			f"({get_percentage(season_stats.users_passed, season_stats.users)}%)"
		)
		embed.description += (
			f"\n> **Contracts passed**: {season_stats.contracts_passed}/{season_stats.contracts} "
			f"({get_percentage(season_stats.contracts_passed, season_stats.contracts)}%)"
		)
		embed.description += "\n\n **Contracts**:"
		for contract_type, type_stats in season_stats.contract_types.items():
			embed.description += f"\n> **{contract_type}**: {get_percentage(type_stats[0], type_stats[1])}% ({type_stats[0]}/{type_stats[1]})"

		return embed

	@contracts_group.command(name="stats", description="Check the current season's stats")
	async def stats(
		self,
		ctx: discord.ApplicationContext,
		rep: discord.Option(
			str,
			description="Optionally check stats for a specific rep",
			required=False,
			autocomplete=get_contracts_reps,
		),  # type: ignore
		hidden: discord.Option(
			bool,
			description="Whether you want the response only visible to you",
			required=False,
		),  # type: ignore
	):
		embed = await self.build_stats_embed(rep)
		if isinstance(embed, str):
			await ctx.respond(embed, ephemeral=True)
		else:
			await ctx.respond(embed=embed, ephemeral=hidden)

	@commands.command(name="stats", help="Check the season's stats", aliases=["s"])
	@commands.cooldown(rate=5, per=5, type=commands.BucketType.user)
	async def stats_text(self, ctx: commands.Context, *, rep: Optional[str] = None):
		embed = await self.build_stats_embed(rep)
		if isinstance(embed, str):
			await ctx.reply(embed)
		else:
			await ctx.reply(embed=embed)

	# ~~PROFILE COMMAND
	async def build_profile_embed(self, ctx, username: str = None):
		member = None
		if username is None:
			member = ctx.author
			username = ctx.author.name
		else:
			if match := re.match(r"<@!?(\d+)>", username):
				user_id = int(match.group(1))
				member = ctx.guild.get_member(user_id) or await self.bot.get_or_fetch_user(user_id)
				if member:
					username = member.name
			else:
				member = get_member_from_username(self.bot, username)

		season, last_updated_timestamp = await get_season_data()
		contract_user = season.get_user(username)
		if not contract_user:
			return "User not found!"

		embed = get_common_embed(last_updated_timestamp, contract_user, member)
		embed.description = f"> **Rep**: {contract_user.rep}"

		contractor: discord.Member = get_member_from_username(self.bot, contract_user.contractor)
		contractees: list[str] = []  # List because theres like a few people that have 2 contractees for some reason
		for user in season.users.values():
			if user.contractor == contract_user.name:
				member = get_member_from_username(self.bot, user.name)
				if member:
					contractees.append(member.mention)
				else:
					contractees.append(user.name)

		embed.description += f"\n> **Contractor**: {contractor.mention if contractor else contract_user.contractor}"
		embed.description += f"\n> **Contractee**: {', '.join(contractees)}"

		if url := contract_user.list_url:
			url_lower = url.lower()
			list_username = url.rstrip("/").split("/")[-1]
			if "myanimelist" in url_lower:
				embed.description += f"\n> **MyAnimeList**: [{list_username}]({url})"
			elif "anilist" in url_lower:
				embed.description += f"\n> **AniList**: [{list_username}]({url})"
			else:
				embed.description += f"\n> **List**: {url}"

		embed.description += f"\n> **Preferences**: {contract_user.preferences}"
		embed.description += f"\n> **Bans**: {contract_user.bans}"

		return embed

	@commands.command(name="profile", aliases=["p"], help="Get a user's profile")
	async def profile_text(self, ctx: commands.Context, username: str = None):
		embed = await self.build_profile_embed(ctx, username)
		if isinstance(embed, str):
			await ctx.reply(embed)
		else:
			await ctx.reply(embed=embed)

	@contracts_group.command(name="profile", description="Get a user's profile")
	async def profile_slash(
		self,
		ctx: discord.ApplicationContext,
		username: discord.Option(
			str,
			description="User to check",
			required=False,
			autocomplete=get_contracts_usernames,
		),  # type: ignore
		hidden: discord.Option(bool, description="Whether you want the response only visible to you", required=False),  # type: ignore
	):
		embed = await self.build_profile_embed(ctx, username)
		if isinstance(embed, str):
			await ctx.respond(embed, ephemeral=True)
		else:
			await ctx.respond(embed=embed, ephemeral=hidden)

	@discord.user_command(name="Get User Profile", guild_ids=BOT_CONFIG.guild_ids)
	async def get_user_profile(self, ctx: discord.ApplicationContext, user: discord.User):
		embed = await self.build_profile_embed(ctx, user.name)
		if isinstance(embed, str):
			await ctx.respond(embed, ephemeral=True)
		else:
			await ctx.respond(embed=embed, ephemeral=True)

	# ~~GET COMMAND
	@contracts_group.command(name="get", description="Get the state of someone's contracts")
	async def get(
		self,
		ctx: discord.ApplicationContext,
		username: discord.Option(
			str,
			description="Optionally check for another user",
			required=False,
			autocomplete=get_contracts_usernames,
		),  # type: ignore
		hidden: discord.Option(
			bool,
			description="Whether you want the response only visible to you",
			required=False,
		),  # type: ignore
	):
		member, actual_username = await _get_contracts_user_and_member(self.bot, ctx.author, username)
		season, _ = await get_season_data()
		contracts_user = season.get_user(actual_username)
		if not contracts_user:
			await ctx.respond(
				embed=discord.Embed(
					title="Contracts",
					color=discord.Color.red(),
					description="User not found! If this is a mistake please ping <@546659584727580692>",
				),
				ephemeral=True,
			)
			return

		await _send_contracts_embed_response(ctx, contracts_user, ctx.author, member, ephemeral=hidden)

	@discord.user_command(name="Get User Contracts", guild_ids=BOT_CONFIG.guild_ids)
	async def get_user_command(self, ctx: discord.ApplicationContext, user: discord.User):
		season, _ = await get_season_data()
		contracts_user = season.get_user(user.name)
		if not contracts_user:
			await ctx.respond(
				embed=discord.Embed(
					title="Contracts",
					color=discord.Color.red(),
					description="User not found! If this is a mistake please ping <@546659584727580692>",
				),
				ephemeral=True,
			)
			return

		await _send_contracts_embed_response(ctx, contracts_user, ctx.author, user, ephemeral=True)

	@commands.command(
		name="get",
		help="Get the state of someone's contracts",
		aliases=["contracts", "g", "c"],
	)
	@commands.cooldown(rate=5, per=5, type=commands.BucketType.user)
	async def get_text(self, ctx: commands.Context, username: str = None):
		member, actual_username = await _get_contracts_user_and_member(self.bot, ctx.author, username)
		season, _ = await get_season_data()
		contracts_user = season.get_user(actual_username)
		if not contracts_user:
			await ctx.reply("User not found!")
			return

		embed = await _create_user_contracts_embed("All", contracts_user, ctx.author, member)
		await ctx.reply(embed=embed)

	# ~~STATUS LOOP
	@tasks.loop(minutes=30)
	async def change_user_status(self):
		season, _ = await get_season_data()
		await self.bot.change_presence(
			status=discord.Status.online,
			activity=discord.CustomActivity(name=f"{season.stats.users_passed}/{season.stats.users} users passed | %help"),
		)
		gc.collect()


def setup(bot: commands.Bot):
	bot.add_cog(Contracts(bot))
