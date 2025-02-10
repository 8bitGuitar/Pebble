import os
import discord
from discord.ext import commands
from openai import OpenAI
from collections import defaultdict
import time
import tempfile
from pathlib import Path
import asyncio
import PyPDF2

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

scalewayClient = OpenAI(
    base_url="https://api.scaleway.ai/b131fbd0-34e0-4a99-a345-931e2eaa426b/v1",
    api_key=os.getenv('SCW_SECRET_KEY') 
)

conversations = defaultdict(list)
fileContexts = defaultdict(str)
lastInteraction = defaultdict(float)

maxHistory = 24
historyExpiry = 86400
maxFileSize = 10 * 1024 * 1024

async def processFile(fileAttachment):
    tempFilePath = None
    try:
        tempFilePath = Path(tempfile.gettempdir()) / f"discord_bot_{time.time()}_{fileAttachment.filename}"
        await fileAttachment.save(str(tempFilePath))
        
        if fileAttachment.filename.endswith('.txt'):
            with open(tempFilePath, 'r', encoding='utf-8') as file:
                text = file.read()
                
        elif fileAttachment.filename.endswith('.pdf'):
            with open(tempFilePath, 'rb') as file:
                pdfReader = PyPDF2.PdfReader(file)
                text = '\n'.join(page.extract_text() for page in pdfReader.pages)
                
        else:
            return f"Unsupported file type: {fileAttachment.filename}. Supported types: .txt, .pdf"
            
        return text[:50000] if len(text) > 50000 else text
        
    finally:
        if tempFilePath and tempFilePath.exists():
            try:
                tempFilePath.unlink()
            except Exception:
                await asyncio.sleep(0.1)
                try:
                    tempFilePath.unlink()
                except Exception:
                    pass

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

def pruneOldConversations():
    currentTime = time.time()
    for userId in list(conversations.keys()):
        if currentTime - lastInteraction[userId] > historyExpiry:
            del conversations[userId]
            del fileContexts[userId]
            del lastInteraction[userId]

@bot.command(name='chat', aliases=['c', "C"])
async def chat(ctx, *, message):
    try:
        async with ctx.typing():
            userId = ctx.author.id
            lastInteraction[userId] = time.time()
            
            if ctx.message.attachments:
                for attachment in ctx.message.attachments:
                    if attachment.size > maxFileSize:
                        await ctx.send(f"File too large. Maximum size is {maxFileSize // (1024*1024)}MB")
                        continue
                    
                    fileContent = await processFile(attachment)
                    if fileContent.startswith("Unsupported file type:"):
                        await ctx.send(fileContent)
                        continue
                        
                    fileContexts[userId] = fileContent
                    await ctx.send(f"File processed and added to context: {attachment.filename}")

            systemContext = (
                f"Context from uploaded files:\n{fileContexts[userId]}\n" if fileContexts[userId] else ""
            ) + (
                "You are a helpful assistant. Please keep your responses concise and format them "
                "for Discord using Markdown where appropriate (e.g., **bold**, *italic*, `code`, etc.)."
            )

            conversations[userId].append({
                "role": "user",
                "content": f"{systemContext}{message}"
            })
            
            if len(conversations[userId]) > maxHistory:
                conversations[userId] = conversations[userId][-maxHistory:]
            
            response = scalewayClient.chat.completions.create(
                model="llama-3.3-70b-instruct",
                messages=conversations[userId],
                temperature=0.6,
                max_tokens=1024,
                stream=True,
            )
            
            full_response = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
            
            conversations[userId].append({
                "role": "assistant",
                "content": full_response
            })
            
            response_chunks = [full_response[i:i+2000] for i in range(0, len(full_response), 2000)]
            
            for chunk in response_chunks:
                await ctx.send(chunk)
            
            pruneOldConversations()
    
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

@bot.command(name='reset')
async def reset(ctx):
    userId = ctx.author.id
    if userId in conversations:
        conversations[userId] = []
        fileContexts[userId] = ""
        await ctx.send("Your conversation history and file context have been reset.")
    else:
        await ctx.send("No conversation history found.")

@bot.command(name='history')
async def history(ctx):
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