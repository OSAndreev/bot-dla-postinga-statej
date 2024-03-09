import asyncio

import httpx
from aiogram import Bot, Dispatcher
from handlers import common
import time
import openai





async def main():
    time.sleep(4)
    bot = Bot(token="#####")
    dp = Dispatcher()
    dp.include_router(common.router)
    await bot.delete_webhook(drop_pending_updates=True)
    common.scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
