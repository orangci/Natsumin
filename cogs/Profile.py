import logging
import re
import discord
from discord.ext import commands
from discord import Option
from contracts import get_season_data
from shared import get_member_from_username
from cogs.Contracts import get_common_embed, get_contracts_usernames, contracts_group
from config import FILE_LOGGING_FORMATTER, CONSOLE_LOGGING_FORMATTER


class Profile(commands.Cog):
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

    async def build_profile_embed(self, ctx, username: str = None):
        member = None
        if username is None:
            member = ctx.author
            username = ctx.author.name
        else:
            if match := re.match(r"<@!?(\d+)>", username):
                user_id = int(match.group(1))
                member = ctx.guild.get_member(
                    user_id
                ) or await self.bot.get_or_fetch_user(user_id)
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

        contractor = discord.utils.get(ctx.guild.members, name=contract_user.contractor)
        embed.description += f"\n> **Contractor**: {contractor.mention if contractor else contract_user.contractor}"

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
            await ctx.reply(embed, delete_after=3)
        else:
            await ctx.reply(embed=embed)

    @contracts_group.command(name="profile", description="Get a user's profile")
    async def profile_slash(
        self,
        ctx: discord.ApplicationContext,
        username: str = Option(
            "User to check", required=False, autocomplete=get_contracts_usernames
        ),
        hidden: bool = Option("Only visible to you", default=False),
    ):
        embed = await self.build_profile_embed(ctx, username)
        if isinstance(embed, str):
            await ctx.respond(embed, ephemeral=True)
        else:
            await ctx.respond(embed=embed, ephemeral=hidden)


def setup(bot: commands.Bot):
    bot.add_cog(Profile(bot))
