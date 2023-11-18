import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from handlers import common





async def main():
    bot = Bot(token="6937186847:AAHGhMg2pPSvcAOsISPu8nun_8pyXWBNNV8")
    dp = Dispatcher()
    dp.include_router(common.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())