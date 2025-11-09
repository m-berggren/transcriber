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


def transcribe(file_path):
    # TODO: Implement transcription logic
    pass


async def finished_recording(sink, channel: discord.TextChannel, *args):
    """
    Callback when recording stops.
    It iterates through every user's audio stream, saves it, transcribes it,
    and then sends the results to the text channel.
    """
    # Note: 'channel' here is passed from the stop_meeting command
    await channel.send("Meeting ended. Processing audio...")

    try:
        for user_id, audio in sink.audio_data.items():
            # Create unique file for each user
            file_path = f"user_{user_id}.wav"
            with open(file_path, 'wb') as f:
                f.write(audio.file.getbuffer())

            # Transcribe the audio file
            transcription = transcribe(file_path)

    except Exception as e:
        await channel.send(f"An error occurred during post-processing: {e}")

@bot.command()
async def start_meeting(ctx):
    if not ctx.author.voice:
        return await ctx.send("You need to be in a voice channel to start a meeting.")

    voice_channel = ctx.author.voice.channel

    # Connect if not already connected
    if not ctx.voice_client:
        voice_client = await voice_channel.connect()
    else:
        voice_client = ctx.voice_client

    await ctx.send(f"Connected to {voice_channel.name} and started recording. Type `!stop_meeting` to end.")

    # Start recording.
    # IMPORTANT: We pass ctx.channel (the text channel) to the callback
    # so the bot knows where to post the transcript when done.
    voice_client.start_recording(
        discord.sinks.WaveSink(),
        finished_recording,
        ctx.channel
    )

@bot.command()
async def stop_meeting(ctx):
    if ctx.voice_client and ctx.voice_client.recording:
        await ctx.send("Stopping recording...")
        ctx.voice_client.stop_recording() # This triggers 'finished_recording'
        # DO NOT disconnect here immediately, wait for processing if you prefer,
        # or disconnect after a short delay.
        # Disconnecting immediately sometimes cuts off the sink callback.
        # For now we'll leave it connected or let the user disconnect it manually if needed,
        # but typically you might want to await the processing before leaving.
    else:
        await ctx.send("I am not currently recording a meeting.")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Disconnected.")


bot.run(TOKEN, log_handler=handler, log_level=logging.DEBUG)
