import os
import asyncio
import logging
import sys

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from config import BOT_TOKEN
from database import init_db
from handlers import common, admin, worker
from scheduler import run_deadline_scheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("taminot_bot")

async def handle_ping(request):
    return web.Response(text="OK - Taminot Bot is running 24/7!", status=200)

async def start_web_server(port: int):
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Veb-server (Render healthcheck) ishga tushdi: port {port}")
    return runner

async def main():
    if not BOT_TOKEN:
        logger.error(
            "XATOLIK: BOT_TOKEN ko'rsatilmagan! .env yoki Desktop faylida BOT_TOKEN ni belgilang."
        )
        print("\n" + "="*50)
        print("DIQQAT: Botni ishga tushirish uchun BOT_TOKEN ni kiriting!")
        print("="*50 + "\n")
        return

    # Initialize Database
    logger.info("Ma'lumotlar bazasi tayyorlanmoqda...")
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Include routers in proper order
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(worker.router)

    # Delete webhook to ensure polling works cleanly
    await bot.delete_webhook(drop_pending_updates=True)

    bot_info = await bot.get_me()
    logger.info(f"Bot muvaffaqiyatli ishga tushdi: @{bot_info.username}")
    print("\n" + "="*50)
    print(f"BOT ISHGA TUSHDI: @{bot_info.username}")
    print("Xodimlar va admin botga /start bosishi mumkin!")
    print("To'xtatish uchun: Ctrl + C")
    print("="*50 + "\n")

    # If PORT is provided (e.g. Render.com cloud environment)
    port_env = os.getenv("PORT")
    web_runner = None
    if port_env and port_env.isdigit():
        web_runner = await start_web_server(int(port_env))

    # Start background deadline reminder scheduler
    scheduler_task = asyncio.create_task(run_deadline_scheduler(bot))

    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        if web_runner:
            await web_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
