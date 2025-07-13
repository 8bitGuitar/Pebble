import os
import time
from collections import defaultdict
from groq import Groq
from fileHandler import processFile

groqClient = Groq(api_key=os.getenv('GROQ_API_KEY'))

conversations = defaultdict(list)
fileContexts = defaultdict(str)
imageContexts = defaultdict(dict)  
imageDescriptions = defaultdict(str)  
lastInteraction = defaultdict(float)

maxHistory = 16
historyExpiry = 86400

def pruneOldConversations():
    currentTime = time.time()
    for userId in list(conversations.keys()):
        if currentTime - lastInteraction[userId] > historyExpiry:
            del conversations[userId]
            del fileContexts[userId]
            del imageContexts[userId]
            del imageDescriptions[userId]
            del lastInteraction[userId]

async def analyzeImageWithVisionModel(imageData, userMessage=""):
    """Use vision model to analyze image and return description"""
    try:
        visionMessages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analyze this image in detail. Describe what you see, including objects, people, text, colors, composition, and any other relevant details. If the user has a specific question about the image, focus on that as well. User's message: {userMessage}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{imageData['base64']}"
                        }
                    }
                ]
            }
        ]

        completion = groqClient.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=visionMessages,
            temperature=0.3,
            max_completion_tokens=499,
        )

        description = completion.choices[0].message.content.strip()
        
        #remove thinking tags if present
        start = description.find("<think>")
        end = description.find("</think>")
        if start != -1 and end != -1:
            description = description[:start] + description[end + len("</think>"):]
        
        return description.strip()
    
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

async def handleChat(ctx, message):
    try:
        async with ctx.typing():
            userId = ctx.author.id
            lastInteraction[userId] = time.time()

            newImageProcessed = False

            if ctx.message.attachments:
                for attachment in ctx.message.attachments:
                    if attachment.size > 10 * 1024 * 1024:
                        await ctx.send("File too large. Maximum size is 10MB.")
                        continue

                    fileContent = await processFile(attachment)
                    
                    # Check for image
                    if isinstance(fileContent, dict) and fileContent.get('type') == 'image':
                        imageContexts[userId] = fileContent
                        processingMessage = await ctx.send(f"📸 Processing image: {attachment.filename}...")
                        
                        imageDescription = await analyzeImageWithVisionModel(fileContent, message)
                        
                        if imageDescription.startswith("Error analyzing image"):
                            await processingMessage.edit(content=imageDescription)
                            continue
                        
                        imageDescriptions[userId] = f"IMAGE ANALYSIS ({attachment.filename}):\n{imageDescription}"
                        newImageProcessed = True
                        await processingMessage.edit(content=f"✅ Image analyzed and added to context: {attachment.filename}")
                        
                    elif isinstance(fileContent, str) and fileContent.startswith("Error processing image"):
                        await ctx.send(fileContent)
                        continue
                    elif fileContent.startswith("Unsupported file type:"):
                        await ctx.send(fileContent)
                        continue
                    else:
                        fileContexts[userId] = fileContent
                        await ctx.send(f"📄 File processed and added to context: {attachment.filename}")

            systemContext = ""
            
            if fileContexts[userId]:
                systemContext += f"DOCUMENT CONTEXT:\n{fileContexts[userId]}\n\n"
            
            if imageDescriptions[userId]:
                systemContext += f"{imageDescriptions[userId]}\n\n"
            
            if systemContext:
                systemContext += "Use the above context when relevant to answer the user's questions. For unrelated questions it is important that you do not mention anything at all about the question being unrelated, just respond normally.\n\n"
            else:
                systemContext = "Answer the user's question normally.\n\n"
            
            systemContext += "You are Pebble, a friendly and helpful assistant. Keep responses concise & clear and use Markdown formatting for Discord."


            userMessage = f"{systemContext}User: {message}"
            
            conversations[userId].append({
                "role": "user",
                "content": userMessage
            })

            if len(conversations[userId]) > maxHistory:
                conversations[userId] = conversations[userId][-maxHistory:]

            # use text model for conversations
            completion = groqClient.chat.completions.create(
                model="llama3-70b-8192",
                messages=conversations[userId],
                temperature=0.5,
                max_completion_tokens=499,
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
        print(f"Error in handleChat: {e}") 
