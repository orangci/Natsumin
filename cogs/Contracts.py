import datetime
import logging
import math
import discord
from typing import Optional
from config import BOT_CONFIG, BASE_EMBED_COLOR, CONSOLE_LOGGING_FORMATTER, FILE_LOGGING_FORMATTER
from discord.ext import commands
import contracts
from contracts import get_season_data, DASHBOARD_ROW_NAMES
from shared import get_member_from_username

contract_categories = {
	"All": ["Base Contract", "Challenge Contract", "Veteran Special", "Movie Special", "VN Special", "Indie Special", "Extreme Special", "Base Buddy", "Challenge Buddy"],
	"Primary": ["Base Contract", "Challenge Contract"],
	"Specials": [
		"Veteran Special", "Movie Special", "VN Special",
		"Indie Special", "Extreme Special"
	],
	"Buddies": ["Base Buddy", "Challenge Buddy"]
}

def get_percentage(num: float, total: float) -> int:
	return math.floor(100 * float(num)/float(total))

async def get_contracts_usernames(ctx: discord.AutocompleteContext): 
	season, _ = get_season_data()
	matching: list[str] = [username.lower() for username in season.users if ctx.value.strip().lower() in username.lower()]
	return matching

async def get_contracts_types(ctx: discord.AutocompleteContext):
	username = ctx.options.get("username")
	if username is None:
		username = ctx.interaction.user.name
	season, _ = get_season_data()
	user = season.get_user(username)
	if not user:
		return []
	return user.contracts.keys()

def get_common_embed(timestamp: float, contracts_user: Optional[contracts.User] = None, discord_member: Optional[discord.Member] = None) -> discord.Embed:
	embed = discord.Embed(color=BASE_EMBED_COLOR)
	if contracts_user:
		#if discord_member:
			#embed.set_thumbnail(url=discord_member.display_avatar.url)
		embed.set_author(
			name=f"{contracts_user.name} {"✅" if contracts_user.status == "PASSED" else "❌" if contracts_user.status == "FAILED" else ""}",
			url=contracts_user.list_url if contracts_user.list_url != "" else None,
			icon_url=discord_member.display_avatar.url if discord_member else None
		)
	"""
	last_updated_datetime = datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
	next_update_datetime = last_updated_datetime + datetime.timedelta(hours=SHEET_DATA_CACHE_DURATION)
	current_datetime = datetime.datetime.now(datetime.UTC)
	difference = next_update_datetime - current_datetime
	difference_seconds = max(difference.total_seconds(), 0)
	hours, remainder = divmod(difference_seconds, 3600)
	minutes, seconds = divmod(remainder, 60)
	embed.set_footer(
		text=f"Data updating in {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}",
		icon_url="https://cdn.discordapp.com/emojis/998705274074435584.webp?size=4096"
	)
	"""
	return embed

def _create_user_contracts_embed(selected_category: str, user: contracts.User, target: discord.Member, enable_inline: bool = True) -> discord.Embed:
	_, last_updated_timestamp = get_season_data()
	embed = get_common_embed(timestamp=last_updated_timestamp, contracts_user=user, discord_member=target)
	#embed.description = f"**Rep:** {user.rep}\n**Contractor:** {user.contractor}\n### Contracts [{len([c for c in user.contracts.values() if c.passed])}/{len(user.contracts)}]"
	for category_contract in contract_categories.get(selected_category):
		if category_contract in user.contracts:
			contract_data = user.contracts.get(category_contract)
			contract_name = contract_data.name
			field_symbol = "✅" if contract_data.passed else "❌"
			if contract_name == "-":
				continue
			elif contract_name == "PLEASE SELECT":
				contract_name = f"__**{contract_name}**__"
				field_symbol = "⚠️"

			embed.add_field(
				name=f"{category_contract} {field_symbol}",
				value=(f"[{contract_name}]({contract_data.review_url})" if contract_data.review_url != "" else contract_name),
				inline=enable_inline
			)

	embed.title = f"Contracts [{len([c for c in user.contracts.values() if c.passed])}/{len(user.contracts)}]"
	return embed

class ContractsView(discord.ui.View):
	def __init__(self, sender: discord.User, contracts_user: contracts.User, target_member: discord.Member):
		super().__init__(timeout=5 * 60, disable_on_timeout=True)
		self.contracts_user = contracts_user
		self.target = target_member
		self.sender = sender
		self.current_category = "Primary"

		categories_to_add: list[dict] = []
		for category, category_contracts in contract_categories.items():
			if category == "All": continue
			contract_category_passed = 0
			contract_category_total = 0
			for contract_type, contract_data in self.contracts_user.contracts.items():
				if contract_type in category_contracts:
					if contract_data.passed:
						contract_category_passed += 1
					contract_category_total += 1

			if contract_category_total > 0:
				categories_to_add.append({
					"name": category,
					"passed": contract_category_passed,
					"total": contract_category_total
				})
		
		self.select_callback.options = [
			discord.SelectOption(
				label=f"{category["name"]} [{category["passed"]}/{category["total"]}]",
				value=category["name"],
				default=True if category["name"] == "Primary" else False,
			) for category in categories_to_add
		]

	@discord.ui.select(
		placeholder="Change contract category"
	)
	async def select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
		#if interaction.user.id != self.sender.id:
			#await interaction.respond("You are not allowed to change the category!",ephemeral=True)
			#return
		selected_category = select.values[0]

		for select_option in select.options:
			select_option.default = False
			if select_option.value == selected_category:
				select_option.default = True	

		await interaction.edit(embed=_create_user_contracts_embed(selected_category, self.contracts_user, self.target, False), view=self)

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
	
	contracts_group = discord.SlashCommandGroup(
		name="contracts",
		description="Contracts related commands",
		guild_ids=BOT_CONFIG.guild_ids,
	)
	#user_group = contracts_group.create_subgroup(
	#	name="user",
	#	description="User contracts related commands",
	#	guild_ids=BOT_CONFIG.guild_ids,
	#)

	@contracts_group.command(name="get", description="Get the state of someone's contracts")
	async def get(
		self, 
		ctx: discord.ApplicationContext, 
		username: discord.Option(str, name="username", description="Optionally check for another user", required=False, autocomplete=get_contracts_usernames), # type: ignore
		is_ephemeral: discord.Option(bool, name="hidden", description="Whether you want the response only visible to you", default=False) # type: ignore
	):
		selected_member: discord.member = None
		if username is None:
			selected_member = ctx.author
			username = ctx.author.name
		else:
			selected_member = get_member_from_username(self.bot, username)
		
		season, _ = get_season_data()
		contracts_user = season.get_user(username)
		if not contracts_user:
			not_found_embed = discord.Embed(title="Contracts", color=discord.Color.red(), description="User not found! If this is a mistake please ping <@546659584727580692>")
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return

		await ctx.respond(
			embed=_create_user_contracts_embed("All", contracts_user, selected_member),
			ephemeral=is_ephemeral,
			#view=ContractsView(
			#	contracts_user=contracts_user,
			#	target_member=selected_member,
			#	sender=ctx.author
			#)
		)

	@contracts_group.command(name="type", description="Get information regarding a type of contract")
	async def type(
		self,
		ctx: discord.ApplicationContext,
		contract_type: discord.Option(str, name="type", description="Type of contract to check", required=True, choices=list(DASHBOARD_ROW_NAMES.values())), # type: ignore
		username: discord.Option(str, name="username", description="User to check", required=False, autocomplete=get_contracts_usernames), # type: ignore
		is_ephemeral: discord.Option(bool, name="hidden", description="Whether you want the response only visible to you", default=False) # type: ignore
	):
		selected_member: discord.Member = None
		if username is None:
			selected_member = ctx.author
			username = ctx.author.name
		else:
			selected_member = get_member_from_username(self.bot, username)
	
		season, last_updated_timestamp = get_season_data()
		contract_user = season.get_user(username)
		if not contract_user:
			not_found_embed = discord.Embed(color=discord.Color.red(), description="User not found! If this is a mistake please ping <@546659584727580692>")
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return

		if contract_type not in contract_user.contracts:
			not_found_embed = discord.Embed(color=discord.Color.red(), description="Contract not found! If this is a mistake please ping <@546659584727580692>")
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return
		
		contract_data = contract_user.contracts[contract_type]

		contracts_embed = get_common_embed(last_updated_timestamp, contract_user, selected_member)
		contracts_embed.title = contract_type
		contracts_embed.url = contract_data.review_url if contract_data.review_url != "" else None
		contracts_embed.description = (
			f"**Name**: {contract_data.name}\n" +
			f"**Medium**: {contract_data.medium}\n" +
			(f"**{"Contractor" if contract_data.medium != "Game" else "Sponsor"}**: {contract_data.contractor}\n" if contract_data.contractor != "" else "")
		)
		contract_status = contract_data.status if contract_data.status != "" else "PENDING"
		contracts_embed.add_field(name="Status", value=contract_status.lower().capitalize(), inline=True)
		contracts_embed.add_field(name="Score", value=contract_data.rating, inline=True)
		contracts_embed.add_field(name="Progress", value=contract_data.progress, inline=True)
		
		await ctx.respond(embed=contracts_embed, ephemeral=is_ephemeral)

	@contracts_group.command(name="profile", description="Get a user's profile")
	async def profile(
		self, 
		ctx: discord.ApplicationContext, 
		username: discord.Option(str, name="username", description="User to check", required=False, autocomplete=get_contracts_usernames), # type: ignore
		is_ephemeral: discord.Option(bool, name="hidden", description="Whether you want the response only visible to you", default=False) # type: ignore
	):
		selected_member: discord.Member = None
		if username is None:
			selected_member = ctx.author
			username = ctx.author.name
		else:
			selected_member = get_member_from_username(self.bot, username)
	
		season, last_updated_timestamp = get_season_data()
		contract_user = season.get_user(username)
		if not contract_user:
			not_found_embed = discord.Embed(title="User Info", color=discord.Color.red(), description="User not found! If this is a mistake please ping <@546659584727580692>")
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return

		contracts_embed = get_common_embed(last_updated_timestamp, contract_user, selected_member)
		contracts_embed.description = (
			f"**Rep**: {contract_user.rep}\n" +
			f"**Contractor**: {contract_user.contractor}\n" +
			(f"**List**: {contract_user.list_url}" if contract_user.list_url != "" else "")
		)
		contracts_embed.add_field(name="Preferences", value=contract_user.preferences, inline=True)
		contracts_embed.add_field(name="Bans", value=contract_user.bans, inline=True)

		await ctx.respond(embed=contracts_embed, ephemeral=is_ephemeral)

	@discord.user_command(name="Get User Contracts", guild_ids=BOT_CONFIG.guild_ids)
	async def get_user_command(self, ctx: discord.ApplicationContext, user: discord.User):		
		season, _ = get_season_data()
		contracts_user = season.get_user(user.name)
		if not contracts_user:
			not_found_embed = discord.Embed(title="Contracts", color=discord.Color.red(), description="User not found! If this is a mistake please ping <@546659584727580692>")
			await ctx.respond(embed=not_found_embed, ephemeral=True)
			return

		await ctx.respond(
			embed=_create_user_contracts_embed("All", contracts_user, user),
			ephemeral=True,
			#view=ContractsView(
			#	contracts_user=contracts_user,
			#	target_member=user,
			#	sender=ctx.author
			#)
		)

	@contracts_group.command(name="stats", description="Check the current season's stats")
	async def stats(
		self, 
		ctx: discord.ApplicationContext, 
		is_ephemeral: discord.Option(bool, name="hidden", description="Whether you want the response only visible to you", default=False) # type: ignore
	):
		season, last_updated_timestamp = get_season_data()
		season_stats = season.stats
		embed = get_common_embed(last_updated_timestamp)
		embed.title = "Contracts Winter 2025"
		embed.description = (
			f"Season ending on **<t:1746943200:D>** at **<t:1746943200:t>**\n" +
			f"Users passed: {season_stats.users_passed}/{season_stats.users} ({get_percentage(season_stats.users_passed,season_stats.users)}%)\n" +
			f"Contracts passed: {season_stats.contracts_passed}/{season_stats.contracts} ({get_percentage(season_stats.contracts_passed,season_stats.contracts)}%)"
		)
		for contract_type, type_stats in season_stats.contract_types.items():
			embed.add_field(name=f"{contract_type} ({get_percentage(type_stats[0], type_stats[1])}%)", value=f"{type_stats[0]}/{type_stats[1]}")
		
		await ctx.respond(embed=embed, ephemeral=is_ephemeral)


	@commands.command(name="get", help="Get the state of someone's contracts", aliases=["contracts", "g", "c"])
	@commands.cooldown(rate=5, per=5, type=commands.BucketType.user)
	async def get_text(self, ctx: commands.Context, username: str = None, enable_upcoming_select: bool = False):
		selected_member: discord.member = None
		if username is None:
			selected_member = ctx.author
			username = ctx.author.name
		else:
			selected_member = get_member_from_username(self.bot, username)
		
		season, _ = get_season_data()
		contracts_user = season.get_user(username)
		if not contracts_user:
			await ctx.reply("User not found!", delete_after=3)
			return

		if not enable_upcoming_select:
			await ctx.reply(embed=_create_user_contracts_embed("All", contracts_user, selected_member))
		else:
			await ctx.reply(
				embed=_create_user_contracts_embed("Primary", contracts_user, selected_member, False),
				view=ContractsView(
					contracts_user=contracts_user,
					target_member=selected_member,
					sender=ctx.author
				)
			)

	@commands.command(name="stats", help="Check the season's stats", aliases=["s"])
	@commands.cooldown(rate=5, per=5, type=commands.BucketType.user)
	async def stats_text(self, ctx: commands.Context):
		season, last_updated_timestamp = get_season_data()
		season_stats = season.stats
		embed = get_common_embed(last_updated_timestamp)
		embed.title = "Contracts Winter 2025"
		embed.description = (
			f"Season ending on **<t:1746943200:D>** at **<t:1746943200:t>**\n" +
			f"Users passed: {season_stats.users_passed}/{season_stats.users} ({get_percentage(season_stats.users_passed,season_stats.users)}%)\n" +
			f"Contracts passed: {season_stats.contracts_passed}/{season_stats.contracts} ({get_percentage(season_stats.contracts_passed,season_stats.contracts)}%)"
		)
		for contract_type, type_stats in season_stats.contract_types.items():
			embed.add_field(name=f"{contract_type} ({get_percentage(type_stats[0], type_stats[1])}%)", value=f"{type_stats[0]}/{type_stats[1]}")
		
		await ctx.reply(embed=embed)

	@commands.command(name="profile", help="Get a user's profile", aliases=["p"])
	@commands.cooldown(rate=5, per=5, type=commands.BucketType.user)
	async def profile_text(self, ctx: commands.Context, username: str = None):
		selected_member: discord.member = None
		if username is None:
			selected_member = ctx.author
			username = ctx.author.name
		else:
			selected_member = get_member_from_username(self.bot, username)
	
		season, last_updated_timestamp = get_season_data()
		contract_user = season.get_user(username)
		if not contract_user:
			await ctx.reply("User not found!", delete_after=3)
			return

		contracts_embed = get_common_embed(last_updated_timestamp, contract_user, selected_member)
		contracts_embed.description = (
			f"**Rep**: {contract_user.rep}\n" +
			f"**Contractor**: {contract_user.contractor}\n" +
			(f"**List**: {contract_user.list_url}" if contract_user.list_url != "" else "")
		)
		contracts_embed.add_field(name="Preferences", value=contract_user.preferences, inline=True)
		contracts_embed.add_field(name="Bans", value=contract_user.bans, inline=True)

		await ctx.reply(embed=contracts_embed)

def setup(bot: commands.Bot):
	bot.add_cog(Contracts(bot))