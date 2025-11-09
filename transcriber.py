import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from vosk import Model, KaldiRecognizer
import wave
import json


load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Load Vosk model
if not os.path.exists(VOSK_MODEL_PATH):
    print(f"Please download a Vosk model and unpack it into a folder named '{VOSK_MODEL_PATH}'")
    exit(1)
print("Loading Vosk model... this might take a moment.")
model = Model(VOSK_MODEL_PATH)
print("Vosk model loaded.")


@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} is ready and online!")


def transcribe(file_path):
    """
    Reads a WAV file and transcribes it using Vosk.
    """
    wf = wave.open(file_path, "rb")

    # Initialize recognizer with the file's framerate (usually 48k for Discord)
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)

    results = []
    # Read file in chunks
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            part_result = json.loads(rec.Result())
            results.append(part_result.get("text", ""))

    # Get the final bit of speech
    final_result = json.loads(rec.FinalResult())
    results.append(final_result.get("text", ""))

    wf.close()

    # Join all the parts together
    return " ".join([r for r in results if r])


async def finished_recording(sink, channel: discord.TextChannel, *args):
    """
    Callback when recording stops.
    It iterates through every user's audio stream, saves it, transcribes it,
    and then sends the results to the text channel.
    """
    # Note: 'channel' here is passed from the stop_meeting command
    await channel.send("Meeting ended. Processing audio...")

    recorded_users = {} # Map user ID to their transcription

    try:
        for user_id, audio in sink.audio_data.items():
            # Create unique file for each user
            file_path = f"user_{user_id}.wav"
            with open(file_path, 'wb') as f:
                f.write(audio.file.getbuffer())

            # Transcribe their specific audio file
            try:
                text = transcribe(file_path)
                if text.strip(): # Only add if they actually said something
                    recorded_users[user_id] = text
                else:
                     recorded_users[user_id] = "(No speech detected)"
            except Exception as e:
                recorded_users[user_id] = f"Error transcribing: {e}"
            finally:
                # Cleanup the temp file
                if os.path.exists(file_path):
                    os.remove(file_path)

        # Format and send the output
        output_message = "**Meeting Transcription:**\n"
        for user_id, text in recorded_users.items():
            output_message += f"<@{user_id}>: {text}\n"

        # Split message if it's too long for Discord (2000 char limit)
        if len(output_message) > 2000:
             # Very basic splitting for demo purposes
             chunks = [output_message[i:i+1900] for i in range(0, len(output_message), 1900)]
             for chunk in chunks:
                 await channel.send(chunk)
        else:
            await channel.send(output_message or "No audio recorded.")

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
