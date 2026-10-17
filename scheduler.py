import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot
from config import UZB_TZ
from database import (
    get_tasks_due_for_reminder,
    get_tasks_overdue,
    mark_task_reminder_sent
)
from keyboards import get_task_actions_keyboard

logger = logging.getLogger("taminot_scheduler")

async def run_deadline_scheduler(bot: Bot):
    """
    Background worker that checks every 60 seconds for tasks due today or approaching deadlines,
    and sends reminders to responsible employees.
    """
    logger.info("Avtomatik eslatmalar xizmati (Scheduler) ishga tushirildi...")
    
    while True:
        try:
            now = datetime.now(UZB_TZ)
            today_str = now.strftime("%Y-%m-%d")
            current_ts_str = now.strftime("%Y-%m-%d %H:%M:%S")

            # 1. Check for tasks due today (or earlier) that haven't been reminded yet (reminder_sent == 0)
            pending_tasks = await get_tasks_due_for_reminder(today_str)
            for t in pending_tasks:
                created_at_str = t["created_at"] or ""
                created_date = created_at_str[:10] if len(created_at_str) >= 10 else ""
                deadline_ts = t["deadline_ts"]

                should_remind = False
                # If task was given on a previous day and deadline is today or earlier -> Remind today!
                if created_date and created_date < today_str:
                    should_remind = True
                # If task was given today with deadline today:
                elif deadline_ts:
                    try:
                        # Check if within 2 hours of deadline or deadline passed
                        dt_deadline = datetime.strptime(deadline_ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UZB_TZ)
                        if now >= (dt_deadline - timedelta(hours=2)):
                            should_remind = True
                    except Exception:
                        should_remind = True
                else:
                    # Generic deadline without specific time -> remind if afternoon
                    if now.hour >= 12:
                        should_remind = True

                if should_remind:
                    emp_tg_id = t["employee_telegram_id"]
                    if emp_tg_id:
                        reminder_text = (
                            f"⏰ <b>ESLATMA: VAZIFA MUDDATI BUGUN!</b>\n"
                            f"────────────────────\n"
                            f"📌 <b>Vazifa #{t['id']}:</b> {t['title']}\n"
                            f"⏳ <b>Muddat:</b> {t['deadline'] or 'Bugun'}\n"
                            f"👑 <b>Topshirdi:</b> {t['creator_name'] or 'Rahbar'}\n"
                            f"────────────────────\n"
                            f"⚠️ <i>Eslatib o'tamiz, bugun ushbu vazifani yakunlash muddati keldi. "
                            f"Agar bajarayotgan bo'lsangiz '⏳ Jarayonda', bajarib bo'lgan bo'lsangiz '✅ Bajarildi' tugmasini bosing:</i>"
                        )
                        try:
                            await bot.send_message(
                                chat_id=emp_tg_id,
                                text=reminder_text,
                                reply_markup=get_task_actions_keyboard(t["id"]),
                                parse_mode="HTML"
                            )
                            logger.info(f"Eslatma yuborildi: Vazifa #{t['id']} -> Xodim ID: {emp_tg_id}")
                        except Exception as e:
                            logger.warning(f"Eslatma yuborishda xato (Vazifa #{t['id']}): {e}")

                    # Mark level 1 reminder as sent so we don't spam
                    await mark_task_reminder_sent(t["id"], level=1)

            # 2. Check for overdue tasks (deadline passed and reminder_sent == 1)
            overdue_tasks = await get_tasks_overdue(current_ts_str)
            for t in overdue_tasks:
                emp_tg_id = t["employee_telegram_id"]
                if emp_tg_id:
                    overdue_text = (
                        f"⚠️ <b>DIQQAT: VAZIFA MUDDATI O'TIB KETDI!</b>\n"
                        f"────────────────────\n"
                        f"📌 <b>Vazifa #{t['id']}:</b> {t['title']}\n"
                        f"⏳ <b>Belgilangan muddat:</b> {t['deadline']}\n"
                        f"👑 <b>Topshirdi:</b> {t['creator_name'] or 'Rahbar'}\n"
                        f"────────────────────\n"
                        f"ℹ️ <i>Vazifa muddati tugadi, ammo botda hali 'Bajarildi' qilinmagan. "
                        f"Iltimos, vazifani tezda yakunlab hisobot bering:</i>"
                    )
                    try:
                        await bot.send_message(
                            chat_id=emp_tg_id,
                            text=overdue_text,
                            reply_markup=get_task_actions_keyboard(t["id"]),
                            parse_mode="HTML"
                        )
                        logger.info(f"Muddati o'tganlik xabari yuborildi: Vazifa #{t['id']} -> Xodim ID: {emp_tg_id}")
                    except Exception as e:
                        logger.warning(f"Muddati o'tganlik xabari xatosi (Vazifa #{t['id']}): {e}")

                # Mark level 2 reminder so overdue notice is sent only once
                await mark_task_reminder_sent(t["id"], level=2)

        except Exception as e:
            logger.error(f"Scheduler siklida kutilmagan xatolik: {e}")

        # Sleep for 60 seconds before next check
        await asyncio.sleep(60)
