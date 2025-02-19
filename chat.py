import os
import time
from collections import defaultdict
from groq import Groq
from fileHandler import processFile

groqClient = Groq(api_key=os.getenv('GROQ_API_KEY'))

conversations = defaultdict(list)
fileContexts = defaultdict(str)
lastInteraction = defaultdict(float)

maxHistory = 16
historyExpiry = 86400

def pruneOldConversations():
    currentTime = time.time()
    for userId in list(conversations.keys()):
        if currentTime - lastInteraction[userId] > historyExpiry:
            del conversations[userId]
            del fileContexts[userId]
            del lastInteraction[userId]

async def handleChat(ctx, message):
    try:
        async with ctx.typing():
            userId = ctx.author.id
            lastInteraction[userId] = time.time()

            if ctx.message.attachments:
                for attachment in ctx.message.attachments:
                    if attachment.size > 10 * 1024 * 1024:
                        await ctx.send("File too large. Maximum size is 10MB.")
                        continue

                    fileContent = await processFile(attachment)
                    if fileContent.startswith("Unsupported file type:"):
                        await ctx.send(fileContent)
                        continue

                    fileContexts[userId] = fileContent
                    await ctx.send(f"File processed and added to context: {attachment.filename}")

            systemContext = (
                f"Context from uploaded files:\n{fileContexts[userId]}\n"
                "If user asks something unrelated to the uploaded file context, answer normally."
                if fileContexts[userId] else ""
            ) + "You are a helpful assistant. Keep responses concise and use Markdown formatting for Discord."

            conversations[userId].append({
                "role": "user",
                "content": f"{systemContext}{message}"
            })

            if len(conversations[userId]) > maxHistory:
                conversations[userId] = conversations[userId][-maxHistory:]

            completion = groqClient.chat.completions.create(
                model="llama3-70b-8192",
                messages=conversations[userId],
                temperature=0.5,
                max_completion_tokens=1024,
            )

            response = completion.choices[0].message.content
            start = response.find("<think>")
            end = response.find("</think>")
            if start != -1 and end != -1:
                response = response[:start] + response[end + len("</think>"):]
            response = response.strip()

            conversations[userId].append({
                "role": "assistant",
                "content": response
            })

            await ctx.send(response)

            pruneOldConversations()

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

