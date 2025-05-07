import datetime
import logging
import re
import discord
from typing import Optional
from config import (
    BOT_CONFIG,
    BASE_EMBED_COLOR,
    CONSOLE_LOGGING_FORMATTER,
    FILE_LOGGING_FORMATTER,
    DEADLINE_TIMESTAMP,
)
from discord.ext import commands
import contracts
from contracts import get_season_data
from shared import get_member_from_username
from cogs.Contracts import get_contracts_usernames, contracts_group

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


def get_common_embed(
    timestamp: float,
    contracts_user: Optional[contracts.User] = None,
    discord_member: Optional[discord.Member] = None,
) -> discord.Embed:
    embed = discord.Embed(color=BASE_EMBED_COLOR, description="")
    if contracts_user:
        embed.set_author(
            name=f"{contracts_user.name} {'✅' if contracts_user.status == 'PASSED' else '❌' if contracts_user.status == 'FAILED' else ''}",
            url=contracts_user.list_url or None,
            icon_url=discord_member.display_avatar.url if discord_member else None,
        )

    now = datetime.datetime.now(datetime.UTC)
    seconds_left = max((DEADLINE_TIMESTAMP - now).total_seconds(), 0)

    if seconds_left > 0:
        days, rem = divmod(seconds_left, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
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
        line += (
            f"[{contract_name}]({contract.review_url})"
            if contract.review_url
            else contract_name
        )
        embed.description += "\n" + line

    if user.status == "PASSED":
        embed.description += "\n\n This user has **passed** the season."

    passed = len([c for c in user.contracts.values() if c.passed])
    total = len(user.contracts)
    embed.title = f"Contracts ({passed}/{total})"

    return embed


async def _get_contracts_user_and_member(
    bot: commands.Bot, ctx_user: discord.Member, username: Optional[str]
):
    if not username:
        return ctx_user, ctx_user.name

    match = re.match(r"<@!?(\d+)>", username)
    if match:
        user_id = int(match.group(1))
        member = ctx_user.guild.get_member(user_id) or await bot.get_or_fetch_user(
            user_id
        )
        return member, member.name if member else None

    return get_member_from_username(bot, username), username


async def _send_contracts_embed_response(
    ctx, user: contracts.User, sender, target, ephemeral=False
):
    embed = await _create_user_contracts_embed("All", user, sender, target)
    await ctx.respond(embed=embed, ephemeral=ephemeral)


class Get(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("bot.contracts")
        if not self.logger.handlers:
            self.logger.addHandler(
                logging.FileHandler("logs/contracts.log", encoding="utf-8")
            )
            self.logger.addHandler(logging.StreamHandler())
            self.logger.handlers[0].setFormatter(FILE_LOGGING_FORMATTER)
            self.logger.handlers[1].setFormatter(CONSOLE_LOGGING_FORMATTER)
            self.logger.setLevel(logging.INFO)

    @contracts_group.command(
        name="get", description="Get the state of someone's contracts"
    )
    async def get(
        self,
        ctx: discord.ApplicationContext,
        username: str = discord.Option(
            "Optionally check for another user",
            required=False,
            autocomplete=get_contracts_usernames,
        ),
        hidden: bool = discord.Option(
            "Whether you want the response only visible to you", default=False
        ),
    ):
        member, actual_username = await _get_contracts_user_and_member(
            self.bot, ctx.author, username
        )
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

        await _send_contracts_embed_response(
            ctx, contracts_user, ctx.author, member, ephemeral=hidden
        )

    @discord.user_command(name="Get User Contracts", guild_ids=BOT_CONFIG.guild_ids)
    async def get_user_command(
        self, ctx: discord.ApplicationContext, user: discord.User
    ):
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

        await _send_contracts_embed_response(
            ctx, contracts_user, ctx.author, user, ephemeral=True
        )

    @commands.command(
        name="get",
        help="Get the state of someone's contracts",
        aliases=["contracts", "g", "c"],
    )
    @commands.cooldown(rate=5, per=5, type=commands.BucketType.user)
    async def get_text(self, ctx: commands.Context, username: str = None):
        member, actual_username = await _get_contracts_user_and_member(
            self.bot, ctx.author, username
        )
        season, _ = await get_season_data()
        contracts_user = season.get_user(actual_username)
        if not contracts_user:
            await ctx.reply("User not found!", delete_after=3)
            return

        embed = await _create_user_contracts_embed(
            "All", contracts_user, ctx.author, member
        )
        await ctx.reply(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Get(bot))
