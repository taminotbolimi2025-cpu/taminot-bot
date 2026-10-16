from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import (
    get_all_employees,
    get_employee_by_id,
    create_task,
    get_all_tasks
)
from keyboards import (
    get_assign_employee_keyboard,
    get_task_actions_keyboard,
    get_task_filter_keyboard,
    get_admin_main_keyboard
)
from handlers.states import TaskCreationStates
from config import ADMIN_IDS
from datetime import datetime

router = Router()

def is_admin_check(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(F.text == "➕ Yangi vazifa berish")
async def start_add_task(message: Message, state: FSMContext):
    if not is_admin_check(message.from_user.id):
        await message.answer("❌ Bu bo'lim faqat rahbar/adminlar uchun!")
        return

    employees = await get_all_employees()

    await state.set_state(TaskCreationStates.waiting_for_worker)
    await message.answer(
        "👤 <b>Vazifani qaysi xodimga topshirasiz?</b>\n\n"
        "🟢 — Botga ulangan\n"
        "⚪️ — Hali start bosmagan\n\n"
        "Kerakli xodimni tanlang:",
        reply_markup=get_assign_employee_keyboard(employees),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("assign_emp:"), TaskCreationStates.waiting_for_worker)
async def process_employee_chosen(callback: CallbackQuery, state: FSMContext):
    emp_id = int(callback.data.split(":")[1])
    emp = await get_employee_by_id(emp_id)
    
    if not emp:
        await callback.answer("Xodim topilmadi!", show_alert=True)
        return

    await state.update_data(
        target_emp_id=emp_id,
        target_name=emp["full_name"],
        target_telegram_id=emp["telegram_id"]
    )
    await state.set_state(TaskCreationStates.waiting_for_task_text)
    
    await callback.message.edit_text(
        f"🎯 Tanlangan xodim: <b>{emp['full_name']}</b>\n\n"
        "📝 Endi <b>vazifani yuboring:</b>\n"
        "• Oddiy matn yozishingiz\n"
        "• Yoki <b>PDF / Excel / fayl / rasm</b> (izoh bilan birga) yuborishingiz mumkin!",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_task_creation")
async def cancel_task_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Vazifa yaratish bekor qilindi.")
    await callback.answer("Bekor qilindi")

@router.message(TaskCreationStates.waiting_for_task_text)
async def process_task_content(message: Message, state: FSMContext, bot: Bot):
    if not is_admin_check(message.from_user.id):
        return

    file_id = None
    file_type = None
    task_text = ""

    if message.document:
        file_id = message.document.file_id
        file_type = "document"
        doc_name = message.document.file_name or "Hujjat (Fayl)"
        task_text = message.caption.strip() if message.caption else f"📄 Biriktirilgan fayl: {doc_name}"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        task_text = message.caption.strip() if message.caption else "🖼 Biriktirilgan rasm"
    elif message.text:
        file_type = "text"
        task_text = message.text.strip()
    else:
        await message.answer("Iltimos, vazifa matnini yozing yoki fayl/rasm yuboring:")
        return

    data = await state.get_data()
    emp_id = data.get("target_emp_id")
    emp_name = data.get("target_name")
    emp_tg_id = data.get("target_telegram_id")
    
    creator_id = message.from_user.id
    creator_name = message.from_user.full_name or "Rahbar"

    # 1. Save task to database with file info
    task_id = await create_task(
        title=task_text,
        description="",
        employee_id=emp_id,
        created_by=creator_id,
        file_id=file_id,
        file_type=file_type
    )

    await state.clear()

    # 2. Notify employee if already connected to bot
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    worker_msg = (
        f"🔔 <b>YANGI VAZIFA #{task_id}!</b>\n"
        f"────────────────────\n"
        f"📝 <b>Vazifa:</b> {task_text}\n"
        f"👑 <b>Topshirdi:</b> {creator_name}\n"
        f"⏰ <b>Vaqt:</b> {now_str}\n"
        f"────────────────────\n"
        f"Vazifani bajargach '✅ Bajarildi' tugmasini bosing yoki boshqaga o'tkazing:"
    )

    sent = False
    if emp_tg_id:
        try:
            if file_type == "document":
                await bot.send_document(
                    chat_id=emp_tg_id,
                    document=file_id,
                    caption=worker_msg,
                    reply_markup=get_task_actions_keyboard(task_id),
                    parse_mode="HTML"
                )
            elif file_type == "photo":
                await bot.send_photo(
                    chat_id=emp_tg_id,
                    photo=file_id,
                    caption=worker_msg,
                    reply_markup=get_task_actions_keyboard(task_id),
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=emp_tg_id,
                    text=worker_msg,
                    reply_markup=get_task_actions_keyboard(task_id),
                    parse_mode="HTML"
                )
            sent = True
        except Exception as e:
            print(f"Xodimga yuborishda xato: {e}")

    # 3. Confirm to Admin
    file_label = " (📎 Fayl biriktirildi)" if file_id else ""
    if sent:
        await message.answer(
            f"✅ <b>Vazifa muvaffaqiyatli topshirildi!</b>\n\n"
            f"👤 <b>Xodim:</b> {emp_name}\n"
            f"📝 <b>Vazifa:</b> {task_text}{file_label}\n\n"
            f"Xodimga xabar yuborildi. U bajarganda guruhga hisobot tushadi.",
            reply_markup=get_admin_main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"✅ <b>Vazifa saqlandi (#{task_id})!</b>\n\n"
            f"👤 <b>Xodim:</b> {emp_name}\n"
            f"📝 <b>Vazifa:</b> {task_text}{file_label}\n\n"
            f"ℹ️ <i>Eslatma: {emp_name} hali botga kirmagan. U botga kirib o'z ismini tanlashi bilan ushbu vazifa unga yuboriladi.</i>",
            reply_markup=get_admin_main_keyboard(),
            parse_mode="HTML"
        )

@router.message(F.text == "👥 Xodimlar ro'yxati")
async def show_employees_list(message: Message):
    if not is_admin_check(message.from_user.id):
        return

    employees = await get_all_employees()
    lines = ["👥 <b>Ta'minot xodimlari ro'yxati:</b>\n"]
    
    for idx, e in enumerate(employees, 1):
        if e["telegram_id"]:
            uname = f" (@{e['username']})" if e["username"] else ""
            status = f"🟢 Ulangan{uname}"
        else:
            status = "⚪️ Hali botga kirmagan"
        lines.append(f"{idx}. <b>{e['full_name']}</b> — <i>{status}</i>")

    lines.append("\n💡 <i>Xodimlar botga kirib o'z ismini tanlaganda, ularning yonida 🟢 paydo bo'ladi.</i>")
    await message.answer("\n".join(lines), parse_mode="HTML")

@router.message(F.text == "📋 Vazifalar nazorati")
async def view_tasks_menu(message: Message):
    if not is_admin_check(message.from_user.id):
        return

    await message.answer(
        "📋 <b>Qaysi vazifalarni ko'rmoqchisiz?</b>",
        reply_markup=get_task_filter_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("filter_tasks:"))
async def filter_tasks_callback(callback: CallbackQuery):
    filter_type = callback.data.split(":")[1]
    tasks = await get_all_tasks(filter_type=filter_type, limit=15)

    title_map = {
        "active": "🔴 Faol vazifalar (Kutilmoqda / Jarayonda)",
        "done": "🟢 Bajarilgan vazifalar",
        "all": "📋 Barcha vazifalar tarixi"
    }

    if not tasks:
        await callback.message.edit_text(
            f"<b>{title_map.get(filter_type, 'Vazifalar')}</b>\n\n"
            "Hozircha bunday vazifalar mavjud emas.",
            reply_markup=get_task_filter_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    text_lines = [f"<b>{title_map.get(filter_type, 'Vazifalar')}</b>\n"]
    for t in tasks:
        status_emoji = "⏳" if t["status"] == "in_progress" else ("✅" if t["status"] == "done" else "🔴")
        status_label = "Jarayonda" if t["status"] == "in_progress" else ("Bajarildi" if t["status"] == "done" else "Kutilmoqda")
        worker = t["employee_name"] or "Noma'lum"
        creator = t["creator_name"] or "Rahbar"
        date_str = t["created_at"] or ""
        file_icon = " 📎[Fayl]" if t["file_id"] else ""

        text_lines.append(
            f"{status_emoji} <b>#{t['id']}</b>{file_icon}: {t['title']}\n"
            f"   👤 <b>Ijrochi:</b> <i>{worker}</i> | Holat: <i>{status_label}</i>\n"
            f"   👑 <b>Topshirdi:</b> <i>{creator}</i>\n"
            f"   📅 <i>{date_str}</i>"
        )

    full_text = "\n\n".join(text_lines)
    await callback.message.edit_text(
        full_text,
        reply_markup=get_task_filter_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
