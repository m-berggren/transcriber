import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os


load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} is ready and online!")


bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)
