from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from database import (
    get_all_employees,
    get_employee_by_telegram_id,
    get_employee_by_id,
    bind_employee,
    get_employee_tasks,
    set_group_id,
    get_group_id
)
from keyboards import (
    get_admin_main_keyboard,
    get_worker_main_keyboard,
    get_bind_employee_keyboard,
    get_task_actions_keyboard
)
from config import ADMIN_IDS

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    if message.chat.type in ("group", "supergroup"):
        await message.reply(
            "👋 Salom! Men Ta'minot bo'limi vazifalar botiman.\n"
            "Bu guruhni vazifalar hisoboti uchun ulash maqsadida /set_group buyrug'ini yuboring."
        )
        return

    user_id = message.from_user.id
    full_name = message.from_user.full_name or message.from_user.first_name

    # 1. Check if user is Admin (Dual role: Admin + Employee)
    if user_id in ADMIN_IDS:
        emp = await get_employee_by_telegram_id(user_id)
        emp_label = f" ({emp['full_name']})" if emp else ""
        text = (
            f"👋 Assalomu alaykum, Hurmatli <b>{full_name}{emp_label}</b>!\n\n"
            "Siz tizimda <b>ham Rahbar (Admin), ham Xodim</b> sifatida faoliyat yuritasiz.\n\n"
            "• <b>➕ Yangi vazifa berish</b> — jamoaga yangi topshiriq yuklash (PDF/matn).\n"
            "• <b>📋 Mening vazifalarim</b> — sizga biriktirilgan vazifalar va ularni '✅ Bajarildi' qilish.\n"
            "• <b>📋 Vazifalar nazorati</b> — kim qaysi ishni qilayotganini kuzatish.\n"
            "• <b>👥 Xodimlar ro'yxati</b> — xodimlar ulanish holati.\n"
            "• <b>⚙️ Guruhni sozlash</b> — hisobot guruhini ulash."
        )
        await message.answer(text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
        return

    # 2. Check if user is already bound to an employee
    emp = await get_employee_by_telegram_id(user_id)
    if emp:
        text = (
            f"👋 Salom, <b>{emp['full_name']}</b>!\n\n"
            "Siz Ta'minot vazifalar tizimiga ulangansiz.\n"
            "Topshirilgan vazifalarni ko'rish uchun pastdagi '📋 Mening vazifalarim' tugmasini bosing."
        )
        await message.answer(text, reply_markup=get_worker_main_keyboard(), parse_mode="HTML")
        return

    # 3. Not bound yet -> Prompt to choose name from pre-saved list
    employees = await get_all_employees()
    text = (
        f"👋 Assalomu alaykum, <b>{full_name}</b>!\n\n"
        "Ta'minot bo'limi vazifalar tizimiga xush kelibsiz.\n\n"
        "👇 <b>Iltimos, pastdagi ro'yxatdan o'z ism-familiyangizni tanlang:</b>"
    )
    await message.answer(text, reply_markup=get_bind_employee_keyboard(employees), parse_mode="HTML")

@router.callback_query(F.data.startswith("bind_me:"))
async def process_bind_employee(callback: CallbackQuery, bot: Bot):
    emp_id = int(callback.data.split(":")[1])
    emp = await get_employee_by_id(emp_id)

    if not emp:
        await callback.answer("Xodim topilmadi!", show_alert=True)
        return

    user_id = callback.from_user.id
    username = callback.from_user.username

    # Bind employee
    await bind_employee(emp_id, user_id, username)

    await callback.message.edit_text(
        f"✅ <b>Muvaffaqiyatli bog'landingiz!</b>\n\n"
        f"👤 Siz: <b>{emp['full_name']}</b>\n\n"
        f"Endi rahbar tomonidan yuklatilgan barcha yangi vazifalar to'g'ridan-to'g'ri shu yerga keladi. "
        f"Vazifani bajarib bo'lgach '✅ Bajarildi' tugmasini bosish kifoya!",
        parse_mode="HTML"
    )

    # If this person is also an Admin, give admin keyboard, otherwise worker keyboard
    kb = get_admin_main_keyboard() if user_id in ADMIN_IDS else get_worker_main_keyboard()
    await callback.message.answer(
        "Asosiy menyu:",
        reply_markup=kb
    )
    await callback.answer("Siz tanlandingiz!")

    # Notify Admins
    for admin_id in ADMIN_IDS:
        uname_str = f" (@{username})" if username else ""
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"🔔 <b>Xodim tizimga ulandi:</b>\n👤 <b>{emp['full_name']}</b>{uname_str}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    # Check for pending tasks already waiting for this employee
    pending_tasks = await get_employee_tasks(emp_id, active_only=True)
    if pending_tasks:
        await callback.message.answer(
            f"🔔 <b>Siz uchun {len(pending_tasks)} ta faol vazifa mavjud:</b>",
            parse_mode="HTML"
        )
        for t in pending_tasks:
            deadline_label = t["deadline"] or "Muddatsiz"
            msg = (
                f"📌 <b>Vazifa #{t['id']}</b>\n"
                f"📝 <b>Matn:</b> {t['title']}\n"
                f"⏳ <b>Muddat:</b> {deadline_label}\n"
                f"📅 <b>Berilgan sana:</b> {t['created_at']}\n\n"
                f"Bajarilgach '✅ Bajarildi' tugmasini bosing:"
            )
            if t["file_id"] and t["file_type"] == "document":
                await bot.send_document(
                    chat_id=user_id,
                    document=t["file_id"],
                    caption=msg,
                    reply_markup=get_task_actions_keyboard(t["id"]),
                    parse_mode="HTML"
                )
            elif t["file_id"] and t["file_type"] == "photo":
                await bot.send_photo(
                    chat_id=user_id,
                    photo=t["file_id"],
                    caption=msg,
                    reply_markup=get_task_actions_keyboard(t["id"]),
                    parse_mode="HTML"
                )
            else:
                await callback.message.answer(
                    msg,
                    reply_markup=get_task_actions_keyboard(t["id"]),
                    parse_mode="HTML"
                )

@router.message(Command("set_group"))
async def cmd_set_group(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("❌ Bu buyruq faqat Telegram guruh ichida ishlatilishi kerak!")
        return

    chat_id = message.chat.id
    chat_title = message.chat.title or "Ta'minot Guruhi"
    
    await set_group_id(chat_id)
    await message.reply(
        f"✅ <b>{chat_title}</b> guruhi muvaffaqiyatli ulandi!\n"
        f"🆔 Guruh ID: <code>{chat_id}</code>\n\n"
        f"Endi xodimlar vazifani bajarganda ('✅ Bajarildi' bosganda), "
        f"bu guruhga avtomatik tarzda hisobot yuboriladi! 🚀",
        parse_mode="HTML"
    )

@router.message(F.text == "⚙️ Guruhni sozlash")
async def show_group_settings(message: Message):
    group_id = await get_group_id()
    status_text = f"✅ Ulangan guruh ID: <code>{group_id}</code>" if group_id else "⚠️ Hozircha guruh ulanmagan."

    text = (
        "⚙️ <b>Vazifalar hisoboti guruhi sozlamasi</b>\n\n"
        f"Holat: {status_text}\n\n"
        "<b>Guruhni qanday ulash mumkin?</b>\n"
        "1. Botni (@taminotvazifabot) Ta'minot Telegram guruhiga a'zo qiling.\n"
        "2. Botga guruhda xabar yozish huquqini (adminlik) bering.\n"
        "3. O'sha guruh ichida <code>/set_group</code> buyrug'ini yuboring.\n\n"
        "Shundan so'ng kim vazifani bajarsa, hisobot darhol shu guruhga tushadi!"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "ℹ️ Bot haqida")
async def show_about(message: Message):
    text = (
        "📦 <b>Ta'minot Bo'limi Vazifalar Boti</b>\n\n"
        "Ushbu bot ta'minot bo'limi xodimlari o'rtasida topshiriqlarni tezkor taqsimlash "
        "va ularning bajarilishini umumiy guruhda shaffof nazorat qilish uchun mo'ljallangan."
    )
    await message.answer(text, parse_mode="HTML")
