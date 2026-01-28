import os
import asyncio
import uvicorn

from app.bot import dp, bot

async def start_bot():
    # polling
    await dp.start_polling(bot)

async def start_api():
    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await asyncio.gather(
        start_api(),
        start_bot(),
    )

if __name__ == "__main__":
    asyncio.run(main())
