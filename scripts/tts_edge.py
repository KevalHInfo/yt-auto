import sys
import asyncio
import edge_tts

text_file = sys.argv[1]
output = sys.argv[2]
voice = sys.argv[3] if len(sys.argv) > 3 else "en-US-JennyNeural"

with open(text_file, "r", encoding="utf-8") as f:
    text = f.read()

async def main():
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output)

asyncio.run(main())
