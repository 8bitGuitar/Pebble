import os
import asyncio
import discord
from discord import app_commands, Embed, Color
from discord.ext import commands
from chat import handleChat
import datetime
# from lyrics import Lyrics  # API issue

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

confession_messages = {}
confession_count = 0

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await register_commands()

async def register_commands():
    try:
        print("Attempting to sync commands...")
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} command(s)")
    except discord.app_commands.errors.CommandSyncFailure as e:
        print(f"Command sync failed with error: {e}")
    except Exception as e:
        print(f"Unexpected error during command sync: {e}")

@bot.command(name='sync')
async def sync(ctx):
    await ctx.send("Attempting to sync commands...")
    try:
        synced = await bot.tree.sync(guild=ctx.guild)
        await ctx.send(f"✅ Successfully synced {len(synced)} command(s) for this server")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync commands: {str(e)}")

@bot.command(name='chat', aliases=['c', 'C'])
async def chat(ctx, *, message):
    await handleChat(ctx, message)

@bot.command(name='reset')
async def reset(ctx):
    from chat import conversations, fileContexts, imageContexts, imageDescriptions
    userId = ctx.author.id
    if userId in conversations:
        conversations[userId] = []
        fileContexts[userId] = ""
        imageContexts[userId] = {}
        imageDescriptions[userId] = ""
        await ctx.send("Your conversation history, file context, image context, and image descriptions have been reset.")
    else:
        await ctx.send("No conversation history found.")

@bot.command(name='history')
async def history(ctx):
    from chat import conversations, fileContexts, imageContexts, imageDescriptions
    userId = ctx.author.id
    if userId in conversations:
        historyLength = len(conversations[userId])
        hasFile = "with" if fileContexts[userId] else "without"
        hasImage = "with" if imageDescriptions[userId] else "without"
        await ctx.send(f"Your conversation has {historyLength} messages, {hasFile} file context, {hasImage} image analysis.")
    else:
        await ctx.send("No conversation history found.")

@bot.tree.command(name="confess", description="Submit an anonymous confession")
@app_commands.describe(confession="Your anonymous confession message")
async def slash_confess(interaction: discord.Interaction, confession: str):
    global confession_count
    await interaction.response.send_message("Your confession has been submitted anonymously.", ephemeral=True)

    confession_count += 1
    confession_id = confession_count

    now = datetime.datetime.now()
    unix_time = int(now.timestamp())

    embed = Embed(description=f"### \n{confession}\n", color=Color.purple())
    embed.set_author(name="Anon Message")
    embed.add_field(name=" ", value=f"Confession #{confession_id}, <t:{unix_time}:R>", inline=True)

    confession_channel = interaction.channel
    sent_message = await confession_channel.send(embed=embed)

    confession_messages[confession_id] = sent_message.id

@bot.tree.command(name="reply", description="Reply anonymously to a confession or another reply")
@app_commands.describe(
    confession_number="The confession number you want to reply to",
    reply="Your anonymous reply"
)
async def anonymous_reply(interaction: discord.Interaction, confession_number: int, reply: str):
    global confession_count
    if confession_number not in confession_messages:
        await interaction.response.send_message(
            f"Confession #{confession_number} not found. Please check the number and try again.", 
            ephemeral=True
        )
        return

    original_message_id = confession_messages[confession_number]

    try:
        original_message = await interaction.channel.fetch_message(original_message_id)
    except discord.NotFound:
        await interaction.response.send_message("The original confession/reply could not be found.", ephemeral=True)
        return

    await interaction.response.send_message("Your anonymous reply has been sent.", ephemeral=True)

    confession_count += 1
    reply_id = confession_count

    now = datetime.datetime.now()
    unix_time = int(now.timestamp())

    embed = Embed(description=f"### \n{reply}\n", color=Color.blue())
    embed.set_author(name=f"Anon Reply to #{confession_number}")
    embed.add_field(name=" ", value=f"Confession #{reply_id}, <t:{unix_time}:R>", inline=True)

    sent_reply = await original_message.reply(embed=embed)
    confession_messages[reply_id] = sent_reply.id

@chat.error
async def chatError(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide a message. Usage: !chat <your message>")

@anonymous_reply.error
async def reply_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.TransformerError):
        await interaction.response.send_message("Please provide a valid confession number.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Error: {str(error)}", ephemeral=True)
        print(f"Reply command error: {error}")


def main():
    discordToken = os.getenv('DISCORD_TOKEN')
    if not discordToken:
        print("ERROR: DISCORD_TOKEN environment variable not set")
        return

    async def start_bot():
        # await bot.add_cog(Lyrics(bot))  #API issue
        await bot.start(discordToken)

    asyncio.run(start_bot())

if __name__ == "__main__":
    main()
