from contracts import get_season_data
from shared import get_member_from_username
from discord.ext import commands, tasks
from typing import Optional
from thefuzz import process
import contracts
import datetime
import logging
import discord
import config
import math
import re


async def _create_user_contracts_embed(user: contracts.User, target: discord.Member, c_season: str = None) -> discord.Embed:
	season, last_updated_timestamp = await get_season_data(c_season)
	embed = get_common_embed(last_updated_timestamp, user, target, c_season)

	for contract_type in contracts.get_contract_types(c_season):
		contract = user.contracts.get(contract_type)
		if not contract or contract.name == "-":
			continue

		symbol = "✅" if contract.passed else "❌"
		if contract.name in ["PLEASE SELECT", "Undecided"]:
			symbol = "⚠️"
			contract_name = f"__**{contract.name}**__"
		else:
			contract_name = contract.name

		if contract_type in contracts.get_optional_contract_types(c_season):
			if contract.passed:
				symbol = "🏆"
			else:
				symbol = "➖"

		line = f"> {symbol} **{contract_type}**: "
		line += f"[{contract_name}]({contract.review_url})" if contract.review_url else contract_name
		embed.description += "\n" + line

	if user.status == "PASSED":
		embed.description += "\n\n This user has **passed** the season."
	elif user.status == "LATE PASS":
		embed.description += "\n\n This user has **passed** the season **late**."

	passed = len([c for c in user.contracts.values() if c.passed])
	total = len(user.contracts)
	embed.title = f"Contracts ({passed}/{total})"

	return embed


async def _get_contracts_user_and_member(bot: commands.Bot, ctx_user: discord.Member, username: Optional[str], c_season: str = None):
	if not username:
		return ctx_user, ctx_user.name

	match = re.match(r"<@!?(\d+)>", username.lower())
	if match:
		user_id = int(match.group(1))
		member = ctx_user.guild.get_member(user_id) or await bot.get_or_fetch_user(user_id)
		return member, member.name if member else None

	season, _ = await get_season_data(c_season)
	contract_user = season.get_user(ctx_user.name)

	if contract_user:
		match username:
			case "[contractee]":
				contractee = contract_user.get_contractee(season)
				username = contractee.name if contractee else ""
			case "[contractor]":
				contractor = contract_user.get_contractor(season)
				username = contractor.name if contractor else ""
			case match if match := (re.match(r"\[(\S*)\.(\S*)]", username) or re.match(r"(\S*)\[(\S*)]", username)):
				check_username, check_type = match.groups()
				if check_user := season.get_user(check_username):
					match check_type:
						case "contractee":
							contractee = check_user.get_contractee(season)
							username = contractee.name if contractee else ""
						case "contractor":
							contractor = check_user.get_contractor(season)
							username = contractor.name if contractor else ""

	return get_member_from_username(bot, username.lower()), username.lower()


async def _send_contracts_embed_response(ctx, user: contracts.User, target, ephemeral=False, c_season: str = None):
	embed = await _create_user_contracts_embed(user, target, c_season)
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
	timestamp: float, contracts_user: Optional[contracts.User] = None, discord_member: Optional[discord.Member] = None, c_season: str = None
) -> discord.Embed:
	embed = discord.Embed(color=config.BASE_EMBED_COLOR, description="")
	if contracts_user:
		# if discord_member:
		# embed.set_thumbnail(url=discord_member.display_avatar.url)
		symbol = ""
		if contracts_user.status == "FAILED":
			symbol = "❌"
		elif contracts_user.status == "PASSED":
			symbol = "✅"
		elif contracts_user.status == "LATE PASS":
			symbol = "⌛☑️"
		elif contracts_user.status == "INCOMPLETE":
			symbol = "⛔"

		if c_season is not None and c_season != config.BOT_CONFIG.active_season:
			symbol += f" ({c_season})" if symbol != "" else f"{(c_season)}"

		embed.set_author(
			name=f"{contracts_user.name} {symbol}",
			url=contracts_user.list_url if contracts_user.list_url != "" else None,
			icon_url=discord_member.display_avatar.url if discord_member else None,
		)

	if c_season is None or c_season == config.BOT_CONFIG.active_season:
		current_datetime = datetime.datetime.now(datetime.UTC)
		difference = config.DEADLINE_TIMESTAMP - current_datetime
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
			embed.set_footer(text="This season has ended.", icon_url="https://cdn.discordapp.com/emojis/998705274074435584.webp?size=4096")
	else:
		embed.set_footer(text="insert text here", icon_url="https://cdn.discordapp.com/emojis/998705274074435584.webp?size=4096")
	return embed


async def build_profile_embed(bot, ctx, username: str = None, c_season: str = None):
	member, actual_username = await _get_contracts_user_and_member(bot, ctx.author, username, c_season)
	season, last_updated_timestamp = await get_season_data(c_season)

	contract_user = season.get_user(actual_username)
	if not contract_user:
		error_embed = discord.Embed(color=discord.Color.red())
		error_embed.description = ":x: User not found!"
		fuzzy_results: list[tuple[str, int]] = process.extract(actual_username, season.users.keys(), limit=1)
		if len(fuzzy_results) > 0:
			fuzzy_username, fuzzy_confidence = fuzzy_results[0]
			error_embed.description = f":x: User not found! Did you mean **{fuzzy_username}** ({fuzzy_confidence}%)?"

		return error_embed

	embed = get_common_embed(last_updated_timestamp, contract_user, member, c_season)
	embed.description = f"> **Rep**: {contract_user.rep}"

	contractor: discord.Member = get_member_from_username(bot, contract_user.contractor)
	contractees: list[str] = []  # List because theres like a few people that have 2 contractees for some reason
	for user in season.users.values():
		if user.contractor == contract_user.name:
			member = get_member_from_username(bot, user.name)
			contractees.append(f"{member.mention} ({user.name})") if member else contractees.append(user.name)

	embed.description += (
		f"\n> **Contractor**: {contractor.mention if contractor else contract_user.contractor} {f'({contractor.name})' if contractor else ''}"
	)
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


async def build_stats_embed(rep: Optional[str] = None, c_season: str = None):
	season, last_updated_timestamp = await get_season_data(c_season)

	if rep and rep.upper() not in season.reps:
		error_embed = discord.Embed(color=discord.Color.red())
		error_embed.description = ":x: Invalid rep!"
		fuzzy_results: list[tuple[str, int]] = process.extract(rep.strip().upper(), season.reps.keys(), limit=1)
		if len(fuzzy_results) > 0:
			fuzzy_rep, fuzzy_confidence = fuzzy_results[0]
			error_embed.description = f":x: Invalid rep! Did you mean **{fuzzy_rep}** ({fuzzy_confidence}%)?"

		return error_embed

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
			users_passed=users_passed, users=users_total, contracts_passed=contracts_passed, contracts=contracts_total, contract_types=contract_types
		)

	embed = get_common_embed(last_updated_timestamp, c_season=c_season)
	c_season = c_season or config.BOT_CONFIG.active_season
	embed.title = f"Contracts {c_season}" if not rep else f"Contracts {c_season} - {rep.upper()} [{season.reps[rep.upper()]}]"
	embed.description = ""

	# if not rep:
	# embed.description += f"\nSeason ending on **<t:{config.DEADLINE_TIMESTAMP_INT}:D>** at **<t:{config.DEADLINE_TIMESTAMP_INT}:t>**."

	embed.description += "\n\n **Passed**:"
	embed.description += (
		f"\n> **Users passed**: {season_stats.users_passed}/{season_stats.users} ({get_percentage(season_stats.users_passed, season_stats.users)}%)"
	)
	embed.description += (
		f"\n> **Contracts passed**: {season_stats.contracts_passed}/{season_stats.contracts} "
		f"({get_percentage(season_stats.contracts_passed, season_stats.contracts)}%)"
	)
	embed.description += "\n\n **Contracts**:"
	for contract_type, type_stats in season_stats.contract_types.items():
		embed.description += f"\n> **{contract_type}**: {type_stats[0]}/{type_stats[1]} ({get_percentage(type_stats[0], type_stats[1])}%)"

	return embed


async def build_leaderboard_embed():
	season, last_updated_timestamp = await get_season_data()

	rep_stats: dict[int, list[str]] = {}
	for rep_name in season.reps.keys():
		users_passed = 0
		users_total = 0
		for user in season.users.values():
			if user.rep.upper() != rep_name.upper():
				continue
			users_total += 1
			if user.status == "PASSED":
				users_passed += 1

		percentage_of_users_passed = get_percentage(users_passed, users_total)
		if percentage_of_users_passed not in rep_stats:
			rep_stats[percentage_of_users_passed] = []
		rep_stats[percentage_of_users_passed].append(f"**{rep_name}** ({users_passed}/{users_total})")

	sorted_stats = dict(sorted(rep_stats.items(), reverse=True))

	embed = get_common_embed(last_updated_timestamp)
	for percentage, reps in sorted_stats.items():
		embed.description += f"\n1. {', '.join(reps)}: {percentage}%"
	return embed


class Contracts(commands.Cog):
	def __init__(self, bot: commands.Bot):
		self.bot = bot
		self.logger = logging.getLogger("bot.contracts")

		if not self.logger.handlers:
			file_handler = logging.FileHandler("logs/contracts.log", encoding="utf-8")
			file_handler.setFormatter(config.FILE_LOGGING_FORMATTER)
			console_handler = logging.StreamHandler()
			console_handler.setFormatter(config.CONSOLE_LOGGING_FORMATTER)
			self.logger.addHandler(file_handler)
			self.logger.addHandler(console_handler)

			self.logger.setLevel(logging.INFO)

	contracts_group = discord.SlashCommandGroup(name="contracts", description="Contracts related commands", guild_ids=config.BOT_CONFIG.guild_ids)

	# ~~TYPE COMMAND
	@contracts_group.command(name="type", description="Get information regarding a type of contract")
	async def type(
		self,
		ctx: discord.ApplicationContext,
		contract_type: discord.Option(
			str, description="Type of contract to check", name="type", required=True, choices=list(contracts.get_contract_types())
		),  # type: ignore
		username: discord.Option(str, description="User to check", required=False, autocomplete=get_contracts_usernames),  # type: ignore
		is_ephemeral: discord.Option(bool, name="hidden", description="Whether you want the response only visible to you", required=False),  # type: ignore
	):
		selected_member: discord.Member = None
		if username is None:
			selected_member = ctx.author
			username = ctx.author.name
		else:
			selected_member = get_member_from_username(self.bot, username)
		username = username.lower()

		season, last_updated_timestamp = await get_season_data()
		contract_user = season.get_user(username)
		if not contract_user:
			return await ctx.respond(embed=discord.Embed(color=discord.Color.red(), description=":x: User not found!"), ephemeral=True)

		if contract_type not in contract_user.contracts:
			return await ctx.respond(embed=discord.Embed(color=discord.Color.red(), description=":x: Contract not found!"), ephemeral=True)

		contract_data = contract_user.contracts[contract_type]
		contractor: discord.Member = get_member_from_username(self.bot, contract_data.contractor)

		embed = get_common_embed(last_updated_timestamp, contract_user, selected_member)
		embed.title = contract_type
		embed.url = contract_data.review_url if contract_data.review_url != "" else None
		embed.description = "> **Name**: " + contract_data.name
		embed.description += f"\n> **Medium**: {contract_data.medium}"
		if contract_data.contractor != "":
			embed.description += f"\n> **{'Contractor' if contract_data.medium != 'Game' else 'Sponsor'}**:"
			embed.description += f" {contractor.mention if contractor else contract_data.contractor} {f'({contractor.name})' if contractor else ''}"
		embed.description += f"\n> **Progress**: {contract_data.progress}"
		embed.description += f"\n> **Score**: {contract_data.rating}"
		embed.description += f"\n> **Status**: {(contract_data.status if contract_data.status != '' else 'PENDING').capitalize()}"

		await ctx.respond(embed=embed, ephemeral=is_ephemeral)

	# ~~STATS COMMAND
	@contracts_group.command(name="stats", description="Check the current season's stats")
	async def stats(
		self,
		ctx: discord.ApplicationContext,
		rep: discord.Option(str, description="Optionally check stats for a specific rep", required=False, autocomplete=get_contracts_reps),  # type: ignore
		c_season: discord.Option(
			str, name="season", description="Optionally check in another season", required=False, choices=contracts.AVAILABLE_SEASONS
		),  # type: ignore
		hidden: discord.Option(bool, description="Whether you want the response only visible to you", required=False),  # type: ignore
	):
		embed = await build_stats_embed(rep, c_season)
		if isinstance(embed, str):
			await ctx.respond(embed, ephemeral=True)
		else:
			await ctx.respond(embed=embed, ephemeral=hidden)

	@commands.command(name="stats", help="Check the season's stats", aliases=["s"])
	@commands.cooldown(rate=5, per=5, type=commands.BucketType.user)
	async def stats_text(self, ctx: commands.Context, *, rep: Optional[str] = None):
		embed = await build_stats_embed(rep)
		if isinstance(embed, str):
			await ctx.reply(embed)
		else:
			await ctx.reply(embed=embed)

	# ~~PROFILE COMMAND
	@commands.command(name="profile", aliases=["p"], help="Get a user's profile")
	async def profile_text(self, ctx: commands.Context, username: str = None):
		embed = await build_profile_embed(self.bot, ctx, username)
		if isinstance(embed, str):
			await ctx.reply(embed)
		else:
			await ctx.reply(embed=embed)

	@contracts_group.command(name="profile", description="Get a user's profile")
	async def profile_slash(
		self,
		ctx: discord.ApplicationContext,
		username: discord.Option(str, description="User to check", required=False, autocomplete=get_contracts_usernames),  # type: ignore
		c_season: discord.Option(
			str, name="season", description="Optionally check in another season", required=False, choices=contracts.AVAILABLE_SEASONS
		),  # type: ignore
		hidden: discord.Option(bool, description="Whether you want the response only visible to you", required=False),  # type: ignore
	):
		embed = await build_profile_embed(self.bot, ctx, username, c_season)
		if isinstance(embed, str):
			await ctx.respond(embed, ephemeral=True)
		else:
			await ctx.respond(embed=embed, ephemeral=hidden)

	@discord.user_command(name="Get User Profile", guild_ids=config.BOT_CONFIG.guild_ids)
	async def get_user_profile(self, ctx: discord.ApplicationContext, user: discord.User):
		embed = await build_profile_embed(self.bot, ctx, user.name)
		if isinstance(embed, str):
			await ctx.respond(embed, ephemeral=True)
		else:
			await ctx.respond(embed=embed, ephemeral=True)

	# ~~GET COMMAND
	@contracts_group.command(name="get", description="Get the state of someone's contracts")
	async def get(
		self,
		ctx: discord.ApplicationContext,
		username: discord.Option(str, description="Optionally check for another user", required=False, autocomplete=get_contracts_usernames),  # type: ignore
		c_season: discord.Option(
			str, name="season", description="Optionally check in another season", required=False, choices=contracts.AVAILABLE_SEASONS
		),  # type: ignore
		hidden: discord.Option(bool, description="Whether you want the response only visible to you", required=False),  # type: ignore
	):
		member, actual_username = await _get_contracts_user_and_member(self.bot, ctx.author, username, c_season)
		season, _ = await get_season_data(c_season)
		contracts_user = season.get_user(actual_username)
		if not contracts_user:
			error_embed = discord.Embed(color=discord.Color.red())
			error_embed.description = ":x: User not found!"
			fuzzy_results: list[tuple[str, int]] = process.extract(actual_username, season.users.keys(), limit=1)
			if len(fuzzy_results) > 0:
				fuzzy_username, fuzzy_confidence = fuzzy_results[0]
				error_embed.description = f":x: User not found! Did you mean **{fuzzy_username}** ({fuzzy_confidence}%)?"

			return await ctx.respond(embed=error_embed, ephemeral=hidden)

		await _send_contracts_embed_response(ctx, contracts_user, member, hidden, c_season=c_season)

	@discord.user_command(name="Get User Contracts", guild_ids=config.BOT_CONFIG.guild_ids)
	async def get_user_command(self, ctx: discord.ApplicationContext, user: discord.User):
		season, _ = await get_season_data()
		contracts_user = season.get_user(user.name)
		if not contracts_user:
			return await ctx.respond(embed=discord.Embed(color=discord.Color.red(), description=":x: User not found!"), ephemeral=True)

		await _send_contracts_embed_response(ctx, contracts_user, user, ephemeral=True)

	@commands.command(name="get", help="Get the state of someone's contracts", aliases=["contracts", "g", "c"])
	@commands.cooldown(rate=5, per=5, type=commands.BucketType.user)
	async def get_text(self, ctx: commands.Context, *, username: str = None):
		member, actual_username = await _get_contracts_user_and_member(self.bot, ctx.author, username)
		season, _ = await get_season_data()
		contracts_user = season.get_user(actual_username)
		if not contracts_user and actual_username.upper() in season.reps.keys():
			return await ctx.reply(
				embed=discord.Embed(
					color=discord.Color.red(), description=f":question: I think you meant to do **{ctx.clean_prefix}s {actual_username.upper()}**"
				)
			)
		elif not contracts_user:
			error_embed = discord.Embed(color=discord.Color.red())
			error_embed.description = ":x: User not found!"
			fuzzy_results: list[tuple[str, int]] = process.extract(actual_username, season.users.keys(), limit=1)
			if len(fuzzy_results) > 0:
				fuzzy_username, fuzzy_confidence = fuzzy_results[0]
				error_embed.description = f":x: User not found! Did you mean **{fuzzy_username}** ({fuzzy_confidence}%)?"
			return await ctx.reply(embed=error_embed)

		embed = await _create_user_contracts_embed(contracts_user, member)
		await ctx.reply(embed=embed)

	# ~~LEADERBOARD COMMAND
	@commands.command(name="leaderboard", help="Check the reps leaderboard", aliases=["lb"])
	async def leaderboard_text(self, ctx: commands.context):
		embed = await build_leaderboard_embed()
		if isinstance(embed, str):
			await ctx.reply(embed)
		else:
			await ctx.reply(embed=embed)

	# ~~STATUS LOOP
	@tasks.loop(minutes=30)
	async def change_user_status(self):
		season, _ = await get_season_data()
		await self.bot.change_presence(
			status=discord.Status.online,
			activity=discord.CustomActivity(name=f"{season.stats.users_passed}/{season.stats.users} users passed | %help"),
		)

	@commands.Cog.listener()
	async def on_ready(self):
		self.change_user_status.start()

	def cog_unload(self):
		self.change_user_status.cancel()


def setup(bot: commands.Bot):
	bot.add_cog(Contracts(bot))
