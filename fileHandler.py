import time
import tempfile
from pathlib import Path
import asyncio
import PyPDF2
import base64
from PIL import Image
import io

async def processFile(file_attachment):
    tempFilePath = None
    try:
        tempFilePath = Path(tempfile.gettempdir()) / f"discord_bot_{time.time()}_{file_attachment.filename}"
        await file_attachment.save(str(tempFilePath))

        # check for image
        if file_attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            return await processImage(tempFilePath, file_attachment.filename)

        elif file_attachment.filename.endswith('.txt'):
            with open(tempFilePath, 'r', encoding='utf-8') as file:
                text = file.read()

        elif file_attachment.filename.endswith('.pdf'):
            with open(tempFilePath, 'rb') as file:
                pdfReader = PyPDF2.PdfReader(file)
                text = '\n'.join(page.extract_text() for page in pdfReader.pages if page.extract_text())

        else:
            return f"Unsupported file type: {file_attachment.filename}. Supported types: .txt, .pdf, .png, .jpg, .jpeg, .gif, .bmp, .webp"

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

async def processImage(imagePath, filename):
    try:
        with Image.open(imagePath) as img:
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # resize if too large
            max_size = 2048
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # base64
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            image_data = buffer.getvalue()
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            return {
                'type': 'image',
                'filename': filename,
                'base64': base64_image,
                'width': img.width,
                'height': img.height,
                'format': 'JPEG'
            }
    
    except Exception as e:
        return f"Error processing image {filename}: {str(e)}"