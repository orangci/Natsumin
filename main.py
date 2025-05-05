import discord
import logging
from discord.ext import commands
from config import BOT_CONFIG, FILE_LOGGING_FORMATTER
import os
from dotenv import load_dotenv

discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.DEBUG)
disc_file_handler = logging.FileHandler("logs/discord.log", encoding="utf-8")
disc_file_handler.setFormatter(FILE_LOGGING_FORMATTER)
discord_logger.addHandler(disc_file_handler)

def clear():
	if os.name == 'nt':
		os.system("cls")
	else:
		os.system("clear")

load_dotenv()
bot = commands.Bot(
	command_prefix=BOT_CONFIG.prefix,
	status=discord.Status.online,
	activity=discord.CustomActivity(name="Doing contracts"),
	intents=discord.Intents.all(),
	case_insensitive=True,
	allowed_mentions=discord.AllowedMentions(
		everyone=False, roles=False, users=True, replied_user=False
	)
)

@bot.event
async def on_ready():
	clear()
	print(f"Logged in as {bot.user.name}#{bot.user.discriminator}!")

def recursive_load_cogs(path: str):
	for file in os.listdir(path):
		if file.endswith(".py") and not file.startswith("_"):
			cog_name = f"{path.replace("/", ".")}.{file[0:-3]}"
			bot.load_extension(cog_name)
			continue
		if os.path.isdir(f"{path}/{file}"):
			recursive_load_cogs(f"{path}/{file}")

recursive_load_cogs("cogs")
bot.run(os.getenv("DISCORD_TOKEN"))