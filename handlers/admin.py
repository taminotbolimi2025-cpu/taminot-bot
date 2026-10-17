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
    get_admin_main_keyboard,
    get_file_comment_keyboard,
    get_deadline_keyboard,
    get_custom_deadline_keyboard
)
from handlers.states import TaskCreationStates
from config import ADMIN_IDS, get_tashkent_str, UZB_TZ
from datetime import datetime, timedelta
import re

router = Router()

def is_admin_check(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def parse_custom_deadline(user_input: str):
    """
    Parses user input into (deadline_str, deadline_date, deadline_ts).
    """
    text = user_input.strip()
    now = datetime.now(UZB_TZ)
    lower = text.lower()

    if "bugun" in lower:
        time_match = re.search(r"(\d{1,2})[:.](\d{2})", text)
        hour = int(time_match.group(1)) if time_match else 18
        minute = int(time_match.group(2)) if time_match else 0
        target = now.replace(hour=hour, minute=minute, second=0)
        return (
            f"Bugun ({target.strftime('%d.%m.%Y')}) {target.strftime('%H:%M')} gacha",
            target.strftime("%Y-%m-%d"),
            target.strftime("%Y-%m-%d %H:%M:%S")
        )

    if "erta" in lower:
        target = now + timedelta(days=1)
        time_match = re.search(r"(\d{1,2})[:.](\d{2})", text)
        hour = int(time_match.group(1)) if time_match else 18
        minute = int(time_match.group(2)) if time_match else 0
        target = target.replace(hour=hour, minute=minute, second=0)
        return (
            f"Ertaga ({target.strftime('%d.%m.%Y')}) {target.strftime('%H:%M')} gacha",
            target.strftime("%Y-%m-%d"),
            target.strftime("%Y-%m-%d %H:%M:%S")
        )

    match_dmy = re.search(r"(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?", text)
    if match_dmy:
        day = int(match_dmy.group(1))
        month = int(match_dmy.group(2))
        year = int(match_dmy.group(3)) if match_dmy.group(3) else now.year
        if year < 100:
            year += 2000

        time_match = re.search(r"(\d{1,2})[:.](\d{2})", text[match_dmy.end():])
        hour = int(time_match.group(1)) if time_match else 18
        minute = int(time_match.group(2)) if time_match else 0

        try:
            target = datetime(year, month, day, hour, minute, 0, tzinfo=UZB_TZ)
            return (
                f"{target.strftime('%d.%m.%Y %H:%M')} gacha",
                target.strftime("%Y-%m-%d"),
                target.strftime("%Y-%m-%d %H:%M:%S")
            )
        except ValueError:
            pass

    fallback_target = now + timedelta(days=1)
    return (
        text,
        fallback_target.strftime("%Y-%m-%d"),
        fallback_target.strftime("%Y-%m-%d 18:00:00")
    )

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
        "• Yoki <b>PDF / Excel / fayl / rasm</b> yuborishingiz mumkin!",
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_task_creation")
async def cancel_task_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Vazifa yaratish bekor qilindi.")
    await callback.answer("Bekor qilindi")

@router.message(TaskCreationStates.waiting_for_task_text)
async def process_task_content(message: Message, state: FSMContext):
    if not is_admin_check(message.from_user.id):
        return

    # Case 1: Document (PDF, Excel, Word, ZIP, etc.)
    if message.document:
        file_id = message.document.file_id
        file_type = "document"
        doc_name = message.document.file_name or "Hujjat (Fayl)"
        caption = message.caption.strip() if message.caption else ""
        
        await state.update_data(
            file_id=file_id,
            file_type=file_type,
            file_name=doc_name,
            initial_caption=caption
        )
        await state.set_state(TaskCreationStates.waiting_for_file_comment)
        
        caption_hint = f"\n\nℹ️ <i>Kiritilgan izoh: {caption}</i>" if caption else ""
        await message.answer(
            f"📎 <b>Fayl qabul qilindi:</b> <code>{doc_name}</code>{caption_hint}\n\n"
            f"📝 <b>Ushbu fayl bo'yicha qanday vazifa yoki izoh (kommentariy) berasiz?</b>\n"
            f"<i>Xodim nima qilishi kerakligini yozib yuboring (yoki pastdagi tugmani bosing):</i>",
            reply_markup=get_file_comment_keyboard(),
            parse_mode="HTML"
        )
        return

    # Case 2: Photo
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        caption = message.caption.strip() if message.caption else ""
        
        await state.update_data(
            file_id=file_id,
            file_type=file_type,
            file_name="Rasm",
            initial_caption=caption
        )
        await state.set_state(TaskCreationStates.waiting_for_file_comment)
        
        caption_hint = f"\n\nℹ️ <i>Kiritilgan izoh: {caption}</i>" if caption else ""
        await message.answer(
            f"🖼 <b>Rasm qabul qilindi!</b>{caption_hint}\n\n"
            f"📝 <b>Ushbu rasm bo'yicha qanday vazifa yoki izoh (kommentariy) berasiz?</b>\n"
            f"<i>Xodim nima qilishi kerakligini yozib yuboring (yoki pastdagi tugmani bosing):</i>",
            reply_markup=get_file_comment_keyboard(),
            parse_mode="HTML"
        )
        return

    # Case 3: Plain text
    if message.text:
        task_text = message.text.strip()
        await state.update_data(
            file_id=None,
            file_type="text",
            task_text=task_text
        )
        await state.set_state(TaskCreationStates.waiting_for_deadline)
        await message.answer(
            f"📝 <b>Vazifa:</b> {task_text}\n\n"
            f"⏳ <b>Vazifaning bajarilish muddati (dedlayn) qachongacha?</b>\n"
            f"Kerakli muddatni tanlang yoki sanani yozib yuboring:",
            reply_markup=get_deadline_keyboard(),
            parse_mode="HTML"
        )
        return

    await message.answer("Iltimos, vazifa matnini yozing yoki fayl/rasm yuboring:")

@router.message(TaskCreationStates.waiting_for_file_comment)
async def process_file_comment_text(message: Message, state: FSMContext):
    if not is_admin_check(message.from_user.id):
        return

    comment = message.text.strip() if message.text else ""
    data = await state.get_data()
    file_name = data.get("file_name", "Fayl")
    
    task_text = comment if comment else f"📄 Biriktirilgan fayl: {file_name}"
    await state.update_data(task_text=task_text)
    await state.set_state(TaskCreationStates.waiting_for_deadline)

    await message.answer(
        f"📝 <b>Vazifa izohi qabul qilindi:</b>\n<i>{task_text}</i>\n\n"
        f"⏳ <b>Vazifaning bajarilish muddati (dedlayn) qachongacha?</b>\n"
        f"Kerakli muddatni tanlang:",
        reply_markup=get_deadline_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "skip_file_comment", TaskCreationStates.waiting_for_file_comment)
async def process_skip_file_comment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    caption = data.get("initial_caption")
    file_name = data.get("file_name", "Fayl")
    
    task_text = caption if caption else f"📄 Biriktirilgan fayl: {file_name}"
    await state.update_data(task_text=task_text)
    await state.set_state(TaskCreationStates.waiting_for_deadline)

    await callback.message.edit_text(
        f"📝 <b>Vazifa:</b> {task_text}\n\n"
        f"⏳ <b>Vazifaning bajarilish muddati (dedlayn) qachongacha?</b>\n"
        f"Kerakli muddatni tanlang:",
        reply_markup=get_deadline_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("deadline_btn:"), TaskCreationStates.waiting_for_deadline)
async def process_deadline_button(callback: CallbackQuery, state: FSMContext, bot: Bot):
    btn = callback.data.split(":")[1]
    now = datetime.now(UZB_TZ)

    if btn == "today":
        deadline_date = now.strftime("%Y-%m-%d")
        deadline_str = f"Bugun ({now.strftime('%d.%m.%Y')}) 18:00 gacha"
        deadline_ts = f"{deadline_date} 18:00:00"
    elif btn == "tomorrow":
        target = now + timedelta(days=1)
        deadline_date = target.strftime("%Y-%m-%d")
        deadline_str = f"Ertaga ({target.strftime('%d.%m.%Y')}) 18:00 gacha"
        deadline_ts = f"{deadline_date} 18:00:00"
    elif btn == "2days":
        target = now + timedelta(days=2)
        deadline_date = target.strftime("%Y-%m-%d")
        deadline_str = f"{target.strftime('%d.%m.%Y')} 18:00 gacha (2 kun)"
        deadline_ts = f"{deadline_date} 18:00:00"
    elif btn == "1week":
        target = now + timedelta(days=7)
        deadline_date = target.strftime("%Y-%m-%d")
        deadline_str = f"{target.strftime('%d.%m.%Y')} 18:00 gacha (1 hafta)"
        deadline_ts = f"{deadline_date} 18:00:00"
    elif btn == "none":
        deadline_str = "Muddatsiz"
        deadline_date = None
        deadline_ts = None
    elif btn == "custom":
        await state.set_state(TaskCreationStates.waiting_for_custom_deadline)
        await callback.message.edit_text(
            "✍️ <b>Iltimos, muddatni yozing:</b>\n\n"
            "<i>Masalan:\n"
            "• <code>Bugun 20:00</code>\n"
            "• <code>Ertaga 15:00</code>\n"
            "• <code>25.10.2026</code>\n"
            "• <code>3 kunda</code></i>",
            reply_markup=get_custom_deadline_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    else:
        await callback.answer()
        return

    await callback.answer()
    await finalize_task_creation(
        state=state,
        bot=bot,
        admin_user=callback.from_user,
        deadline_str=deadline_str,
        deadline_date=deadline_date,
        deadline_ts=deadline_ts,
        edit_message=callback.message
    )

@router.message(TaskCreationStates.waiting_for_deadline)
async def process_deadline_direct_text(message: Message, state: FSMContext, bot: Bot):
    if not is_admin_check(message.from_user.id):
        return

    deadline_str, deadline_date, deadline_ts = parse_custom_deadline(message.text)
    await finalize_task_creation(
        state=state,
        bot=bot,
        admin_user=message.from_user,
        deadline_str=deadline_str,
        deadline_date=deadline_date,
        deadline_ts=deadline_ts,
        reply_message=message
    )

@router.message(TaskCreationStates.waiting_for_custom_deadline)
async def process_custom_deadline_input(message: Message, state: FSMContext, bot: Bot):
    if not is_admin_check(message.from_user.id):
        return

    deadline_str, deadline_date, deadline_ts = parse_custom_deadline(message.text)
    await finalize_task_creation(
        state=state,
        bot=bot,
        admin_user=message.from_user,
        deadline_str=deadline_str,
        deadline_date=deadline_date,
        deadline_ts=deadline_ts,
        reply_message=message
    )

async def finalize_task_creation(
    state: FSMContext,
    bot: Bot,
    admin_user,
    deadline_str: str,
    deadline_date: str,
    deadline_ts: str,
    edit_message: Message = None,
    reply_message: Message = None
):
    data = await state.get_data()
    emp_id = data.get("target_emp_id")
    emp_name = data.get("target_name")
    emp_tg_id = data.get("target_telegram_id")
    task_text = data.get("task_text", "")
    file_id = data.get("file_id")
    file_type = data.get("file_type")

    creator_id = admin_user.id
    creator_name = admin_user.full_name or "Rahbar"

    # 1. Save to Database
    task_id = await create_task(
        title=task_text,
        description="",
        employee_id=emp_id,
        created_by=creator_id,
        file_id=file_id,
        file_type=file_type,
        deadline=deadline_str,
        deadline_date=deadline_date,
        deadline_ts=deadline_ts
    )

    await state.clear()

    # 2. Notify Employee
    now_str = get_tashkent_str()
    worker_msg = (
        f"🔔 <b>YANGI VAZIFA #{task_id}!</b>\n"
        f"────────────────────\n"
        f"📝 <b>Vazifa:</b> {task_text}\n"
        f"⏳ <b>Muddat:</b> {deadline_str}\n"
        f"👑 <b>Topshirdi:</b> {creator_name}\n"
        f"⏰ <b>Berilgan vaqt:</b> {now_str}\n"
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
        confirm_text = (
            f"✅ <b>Vazifa muvaffaqiyatli topshirildi!</b>\n\n"
            f"👤 <b>Xodim:</b> {emp_name}\n"
            f"📝 <b>Vazifa:</b> {task_text}{file_label}\n"
            f"⏳ <b>Muddat:</b> {deadline_str}\n\n"
            f"Xodimga xabar yuborildi. U bajarganda guruhga hisobot tushadi."
        )
    else:
        confirm_text = (
            f"✅ <b>Vazifa saqlandi (#{task_id})!</b>\n\n"
            f"👤 <b>Xodim:</b> {emp_name}\n"
            f"📝 <b>Vazifa:</b> {task_text}{file_label}\n"
            f"⏳ <b>Muddat:</b> {deadline_str}\n\n"
            f"ℹ️ <i>Eslatma: {emp_name} hali botga kirmagan. U botga kirib o'z ismini tanlashi bilan ushbu vazifa unga yuboriladi.</i>"
        )

    if edit_message:
        try:
            await edit_message.edit_text(confirm_text, parse_mode="HTML")
            await edit_message.answer("Asosiy menyu:", reply_markup=get_admin_main_keyboard())
        except Exception:
            await edit_message.answer(confirm_text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    elif reply_message:
        await reply_message.answer(confirm_text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")

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
        deadline_label = t["deadline"] or "Muddatsiz"
        file_icon = " 📎[Fayl]" if t["file_id"] else ""

        text_lines.append(
            f"{status_emoji} <b>#{t['id']}</b>{file_icon}: {t['title']}\n"
            f"   👤 <b>Ijrochi:</b> <i>{worker}</i> | Holat: <i>{status_label}</i>\n"
            f"   ⏳ <b>Muddat:</b> <i>{deadline_label}</i>\n"
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
