import os
import discord
from discord.ext import commands
from chat import handleChat


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='chat', aliases=['c', 'C'])
async def chat(ctx, *, message):
    await handleChat(ctx, message)

@bot.command(name='reset')
async def reset(ctx):
    from chat import conversations, fileContexts
    userId = ctx.author.id
    if userId in conversations:
        conversations[userId] = []
        fileContexts[userId] = ""
        await ctx.send("Your conversation history and file context have been reset.")
    else:
        await ctx.send("No conversation history found.")

@bot.command(name='history')
async def history(ctx):
    from chat import conversations, fileContexts
    userId = ctx.author.id
    if userId in conversations:
        historyLength = len(conversations[userId])
        hasFile = "with" if fileContexts[userId] else "without"
        await ctx.send(f"Your conversation has {historyLength} messages, {hasFile} file context.")
    else:
        await ctx.send("No conversation history found.")

@chat.error
async def chatError(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide a message. Usage: !chat <your message>")

def main():
    discordToken = os.getenv('DISCORD_TOKEN')
    bot.run(discordToken)

if __name__ == "__main__":
    main()
