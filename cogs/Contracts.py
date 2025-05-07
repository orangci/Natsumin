import datetime
import gc
import logging
import discord
import discord.utils
from typing import Optional
from config import (
    BOT_CONFIG,
    BASE_EMBED_COLOR,
    CONSOLE_LOGGING_FORMATTER,
    FILE_LOGGING_FORMATTER,
    DEADLINE_TIMESTAMP,
)
from discord.ext import commands, tasks
import contracts
from contracts import get_season_data, DASHBOARD_ROW_NAMES
from shared import get_member_from_username

contracts_group = discord.SlashCommandGroup(
    "contracts",
    "Contracts related commands",
    guild_ids=BOT_CONFIG.guild_ids,
)


async def get_contracts_usernames(ctx: discord.AutocompleteContext):
    season, _ = await get_season_data()
    matching: list[str] = [
        username.lower()
        for username in season.users
        if ctx.value.strip().lower() in username.lower()
    ]
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

    @contracts_group.command(
        name="type", description="Get information regarding a type of contract"
    )
    async def type(
        self,
        ctx: discord.ApplicationContext,
        contract_type: str = discord.Option(
            name="type",
            description="Type of contract to check",
            required=True,
            choices=list(DASHBOARD_ROW_NAMES.values()),
        ),
        username: str = discord.Option(
            name="username",
            description="User to check",
            required=False,
            autocomplete=get_contracts_usernames,
        ),
        is_ephemeral: bool = discord.Option(
            name="hidden",
            description="Whether you want the response only visible to you",
            default=False,
        ),
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

        contracts_embed = get_common_embed(
            last_updated_timestamp, contract_user, selected_member
        )
        contracts_embed.title = contract_type
        contracts_embed.url = (
            contract_data.review_url if contract_data.review_url != "" else None
        )
        contracts_embed.description = (
            f"**Name**: {contract_data.name}\n"
            + f"**Medium**: {contract_data.medium}\n"
            + (
                f"**{'Contractor' if contract_data.medium != 'Game' else 'Sponsor'}**: {contract_data.contractor}\n"
                if contract_data.contractor != ""
                else ""
            )
        )
        contract_status = (
            contract_data.status if contract_data.status != "" else "PENDING"
        )
        contracts_embed.add_field(
            name="Status", value=contract_status.lower().capitalize(), inline=True
        )
        contracts_embed.add_field(name="Score", value=contract_data.rating, inline=True)
        contracts_embed.add_field(
            name="Progress", value=contract_data.progress, inline=True
        )

        await ctx.respond(embed=contracts_embed, ephemeral=is_ephemeral)

    @tasks.loop(minutes=30)
    async def change_user_status(self):
        season, _ = await get_season_data()
        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.CustomActivity(
                name=f"{season.stats.users_passed}/{season.stats.users} users passed | %help"
            ),
        )
        gc.collect()


def setup(bot: commands.Bot):
    bot.add_cog(Contracts(bot))
