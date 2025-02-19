import time
import tempfile
from pathlib import Path
import asyncio
import PyPDF2

async def processFile(file_attachment):
    tempFilePath = None
    try:
        tempFilePath = Path(tempfile.gettempdir()) / f"discord_bot_{time.time()}_{file_attachment.filename}"
        await file_attachment.save(str(tempFilePath))

        if file_attachment.filename.endswith('.txt'):
            with open(tempFilePath, 'r', encoding='utf-8') as file:
                text = file.read()

        elif file_attachment.filename.endswith('.pdf'):
            with open(tempFilePath, 'rb') as file:
                pdfReader = PyPDF2.PdfReader(file)
                text = '\n'.join(page.extract_text() for page in pdfReader.pages if page.extract_text())

        else:
            return f"Unsupported file type: {file_attachment.filename}. Supported types: .txt, .pdf"

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
