import discord
from discord.ext import commands
from config import BOT_CONFIG
import os
from dotenv import load_dotenv

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
	allowed_mentions=discord.AllowedMentions(
		everyone=False, roles=False, users=True, replied_user=True
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