import logging
import math
import discord
import discord.utils
from typing import Optional
from config import (
    CONSOLE_LOGGING_FORMATTER,
    FILE_LOGGING_FORMATTER,
    DEADLINE_TIMESTAMP_INT,
)
from discord.ext import commands
import contracts
from contracts import get_season_data
from cogs.Contracts import get_common_embed, contracts_group


def get_percentage(num: float, total: float) -> int:
    return math.floor(100 * float(num) / float(total))


async def get_contracts_reps(ctx: discord.AutocompleteContext):
    season, _ = await get_season_data()
    return [
        rep.upper() for rep in season.reps if ctx.value.strip().lower() in rep.lower()
    ]


class Stats(commands.Cog):
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

    async def build_stats_embed(self, rep: Optional[str] = None):
        season, last_updated_timestamp = await get_season_data()

        if rep and rep.lower() not in [r.lower() for r in season.reps]:
            return "Invalid rep!"

        if not rep:
            season_stats = season.stats
        else:
            users_passed = users_total = contracts_passed = contracts_total = 0
            contract_types = {}

            for user in season.users.values():
                if user.rep.lower() != rep.lower():
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
        embed.title = (
            "Contracts Winter 2025"
            if not rep
            else f"Contracts Winter 2025 - {rep.upper()}"
        )
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
            embed.description += (
                f"\n> **{contract_type}**: {get_percentage(type_stats[0], type_stats[1])}% "
                f"({type_stats[0]}/{type_stats[1]})"
            )

        return embed

    @contracts_group.command(
        name="stats", description="Check the current season's stats"
    )
    async def stats(
        self,
        ctx: discord.ApplicationContext,
        rep: str = discord.Option(
            "Optionally check stats for a specific rep",
            required=False,
            autocomplete=get_contracts_reps,
        ),
        is_ephemeral: bool = discord.Option(
            "Whether you want the response only visible to you",
            default=False,
        ),
    ):
        embed = await self.build_stats_embed(rep)
        if isinstance(embed, str):
            await ctx.respond(embed, ephemeral=True)
        else:
            await ctx.respond(embed=embed, ephemeral=is_ephemeral)

    @commands.command(name="stats", help="Check the season's stats", aliases=["s"])
    @commands.cooldown(rate=5, per=5, type=commands.BucketType.user)
    async def stats_text(self, ctx: commands.Context, *, rep: Optional[str] = None):
        embed = await self.build_stats_embed(rep)
        if isinstance(embed, str):
            await ctx.reply(embed, delete_after=3)
        else:
            await ctx.reply(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(Stats(bot))
