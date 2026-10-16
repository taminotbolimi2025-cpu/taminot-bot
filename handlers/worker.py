from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import (
    get_task,
    update_task_status,
    complete_task,
    get_employee_tasks,
    get_employee_by_telegram_id,
    get_employee_by_id,
    get_all_employees,
    reassign_task,
    get_group_id
)
from keyboards import (
    get_task_actions_keyboard,
    get_reassign_employee_keyboard,
    get_completion_report_keyboard
)
from handlers.states import TaskCompletionStates
from config import get_tashkent_str

router = Router()

@router.callback_query(F.data.startswith("task_done:"))
async def process_task_done_start(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    task = await get_task(task_id)

    if not task:
        await callback.answer("Vazifa topilmadi!", show_alert=True)
        return

    # Check if already done
    if task["status"] == "done":
        await callback.answer("Bu vazifa allaqachon bajarilgan!", show_alert=True)
        return

    await state.set_state(TaskCompletionStates.waiting_for_report)
    await state.update_data(completing_task_id=task_id)

    prompt_text = (
        f"📎 <b>VAZIFANI YAKUNLASH #{task_id}</b>\n\n"
        f"📝 <b>Vazifa:</b> {task['title']}\n\n"
        "Iltimos, <b>hisobot yoki tasdiqlovchi faylni yuboring:</b>\n"
        "• <b>Yangilangan fayl</b> (to'ldirilgan Excel, imzolangan PDF va h.k.)\n"
        "• <b>Yoki fotosurat</b> (chek, nakladnoy, tovar rasmi)\n"
        "• <b>Yoki qisqa izoh/matn</b> yozishingiz mumkin.\n\n"
        "<i>(Agar fayl talab qilinmasa, pastdagi tugmani bosing):</i>"
    )

    try:
        if callback.message.caption:
            await callback.message.edit_caption(
                caption=prompt_text,
                reply_markup=get_completion_report_keyboard(task_id),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                prompt_text,
                reply_markup=get_completion_report_keyboard(task_id),
                parse_mode="HTML"
            )
    except Exception:
        await callback.message.answer(
            prompt_text,
            reply_markup=get_completion_report_keyboard(task_id),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_completion:"))
async def cancel_completion(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    await state.clear()
    task = await get_task(task_id)
    if not task:
        await callback.message.delete()
        return

    restore_text = (
        f"📌 <b>Vazifa #{task['id']}</b>\n"
        f"📝 <b>Matn:</b> {task['title']}\n"
        f"Holat: <i>Kutilmoqda / Jarayonda</i>"
    )
    try:
        if callback.message.caption:
            await callback.message.edit_caption(
                caption=restore_text,
                reply_markup=get_task_actions_keyboard(task_id),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                restore_text,
                reply_markup=get_task_actions_keyboard(task_id),
                parse_mode="HTML"
            )
    except Exception:
        pass
    await callback.answer("Bekor qilindi")

@router.callback_query(F.data.startswith("skip_report:"))
async def process_skip_report(callback: CallbackQuery, state: FSMContext, bot: Bot):
    task_id = int(callback.data.split(":")[1])
    await state.clear()
    await finish_task_submission(
        task_id=task_id,
        comment="Faylsiz tasdiqlandi",
        file_id=None,
        file_type=None,
        user=callback.from_user,
        message_to_edit=callback.message,
        bot=bot
    )
    await callback.answer("✅ Vazifa bajarildi!")

@router.message(TaskCompletionStates.waiting_for_report)
async def process_report_file(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    task_id = data.get("completing_task_id")
    if not task_id:
        await state.clear()
        return

    file_id = None
    file_type = None
    comment = ""

    if message.document:
        file_id = message.document.file_id
        file_type = "document"
        doc_name = message.document.file_name or "Hujjat"
        comment = message.caption.strip() if message.caption else f"📎 Yangilangan fayl: {doc_name}"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        comment = message.caption.strip() if message.caption else "📷 Foto-hisobot biriktirildi"
    elif message.text:
        comment = message.text.strip()
    else:
        await message.answer("Iltimos, fayl, rasm yoki matn yuboring (yoki bekor qiling):")
        return

    await state.clear()
    await finish_task_submission(
        task_id=task_id,
        comment=comment,
        file_id=file_id,
        file_type=file_type,
        user=message.from_user,
        message_to_edit=None,
        bot=bot,
        user_message=message
    )

async def finish_task_submission(task_id: int, comment: str, file_id: str, file_type: str, user, message_to_edit, bot: Bot, user_message=None):
    task = await get_task(task_id)
    if not task:
        return

    # Update in DB
    await complete_task(task_id, comment=comment, file_id=file_id, file_type=file_type)
    now_str = get_tashkent_str()

    worker_name = task["employee_name"] or user.full_name
    task_title = task["title"]
    creator_id = task["created_by"]

    # 1. Update UI for the worker
    file_note = f"\n📎 <b>Hisobot:</b> {comment}" if comment else ""
    worker_confirm_text = (
        f"✅ <b>VAZIFA BAJARILDI!</b>\n"
        f"────────────────────\n"
        f"📝 <b>Vazifa:</b> {task_title}"
        f"{file_note}\n"
        f"⏱ <b>Bajarilgan vaqt:</b> {now_str}\n"
        f"────────────────────\n"
        f"<i>Rahmat, hisobot qabul qilindi!</i>"
    )

    if message_to_edit:
        try:
            if message_to_edit.caption:
                await message_to_edit.edit_caption(caption=worker_confirm_text, parse_mode="HTML")
            else:
                await message_to_edit.edit_text(worker_confirm_text, parse_mode="HTML")
        except Exception:
            pass
    elif user_message:
        await user_message.answer(worker_confirm_text, parse_mode="HTML")

    # 2. Notify the Task Creator / Admin
    admin_alert = (
        f"✅ <b>Xodim vazifani bajardi!</b>\n"
        f"────────────────────\n"
        f"📌 <b>Vazifa #{task_id}:</b> {task_title}\n"
        f"👤 <b>Xodim:</b> {worker_name}\n"
        f"💬 <b>Natija/Hisobot:</b> {comment or 'Tasdiqlandi'}\n"
        f"⏱ <b>Vaqt:</b> {now_str}\n"
        f"────────────────────"
    )

    if creator_id and creator_id != user.id:
        try:
            if file_id and file_type == "document":
                await bot.send_document(chat_id=creator_id, document=file_id, caption=admin_alert, parse_mode="HTML")
            elif file_id and file_type == "photo":
                await bot.send_photo(chat_id=creator_id, photo=file_id, caption=admin_alert, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=creator_id, text=admin_alert, parse_mode="HTML")
        except Exception as e:
            print(f"Adminga yuborishda xato: {e}")

    # 3. Post to Ta'minot Group
    group_id = await get_group_id()
    if group_id:
        group_alert = (
            f"🎉 <b>VAZIFA BAJARILDI!</b>\n"
            f"────────────────────\n"
            f"👤 <b>Xodim:</b> {worker_name}\n"
            f"📝 <b>Vazifa:</b> {task_title}\n"
            f"💬 <b>Hisobot:</b> {comment or 'Bajarildi'}\n"
            f"⏱ <b>Bajarildi:</b> {now_str}\n"
            f"────────────────────\n"
            f"✅ <i>Ta'minot bo'limi nazorati ostida</i>"
        )
        try:
            if file_id and file_type == "document":
                await bot.send_document(chat_id=group_id, document=file_id, caption=group_alert, parse_mode="HTML")
            elif file_id and file_type == "photo":
                await bot.send_photo(chat_id=group_id, photo=file_id, caption=group_alert, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=group_id, text=group_alert, parse_mode="HTML")
        except Exception as e:
            print(f"Guruhga yuborishda xato: {e}")

@router.callback_query(F.data.startswith("task_progress:"))
async def process_task_progress(callback: CallbackQuery, bot: Bot):
    task_id = int(callback.data.split(":")[1])
    task = await get_task(task_id)

    if not task:
        await callback.answer("Vazifa topilmadi!", show_alert=True)
        return

    if task["status"] == "done":
        await callback.answer("Bu vazifa allaqachon bajarilgan!", show_alert=True)
        return

    await update_task_status(task_id, "in_progress")
    await callback.answer("⏳ Holat 'Jarayonda' deb o'zgartirildi!")

    task_title = task["title"]
    now_str = get_tashkent_str()

    progress_text = (
        f"⏳ <b>VAZIFA JARAYONDA</b>\n"
        f"────────────────────\n"
        f"📝 <b>Vazifa:</b> {task_title}\n"
        f"⏱ <b>Boshlandi:</b> {now_str}\n"
        f"────────────────────\n"
        f"Vazifa tugagach, pastdagi tugmani bosing:"
    )
    try:
        if callback.message.caption:
            await callback.message.edit_caption(
                caption=progress_text,
                reply_markup=get_task_actions_keyboard(task_id),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                progress_text,
                reply_markup=get_task_actions_keyboard(task_id),
                parse_mode="HTML"
            )
    except Exception:
        pass

@router.callback_query(F.data.startswith("task_reassign:"))
async def process_start_reassign(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    task = await get_task(task_id)

    if not task:
        await callback.answer("Vazifa topilmadi!", show_alert=True)
        return

    if task["status"] == "done":
        await callback.answer("Bajarilgan vazifani boshqaga o'tkazib bo'lmaydi!", show_alert=True)
        return

    employees = await get_all_employees()
    kb = get_reassign_employee_keyboard(task_id, employees, current_emp_id=task["employee_id"])

    text = (
        f"🔄 <b>Vazifani boshqa xodimga o'tkazish</b>\n\n"
        f"📝 <b>Vazifa:</b> {task['title']}\n\n"
        f"Ushbu vazifani kimga yuklamoqchisiz? Tanlang:"
    )

    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("do_reassign:"))
async def process_execute_reassign(callback: CallbackQuery, bot: Bot):
    _, task_id_str, new_emp_id_str = callback.data.split(":")
    task_id = int(task_id_str)
    new_emp_id = int(new_emp_id_str)

    task = await get_task(task_id)
    if not task:
        await callback.answer("Vazifa topilmadi!", show_alert=True)
        return

    new_emp = await get_employee_by_id(new_emp_id)
    if not new_emp:
        await callback.answer("Tanlangan xodim topilmadi!", show_alert=True)
        return

    old_worker_name = task["employee_name"] or callback.from_user.full_name
    new_worker_name = new_emp["full_name"]
    creator_name = task["creator_name"] or "Rahbar"
    creator_id = task["created_by"]

    # 1. Update DB
    await reassign_task(task_id, new_emp_id)

    # 2. Update current worker's UI
    done_reassign_text = (
        f"🔄 <b>VAZIFA #{task_id} BOSHQAGA O'TKAZILDI!</b>\n"
        f"────────────────────\n"
        f"📝 <b>Vazifa:</b> {task['title']}\n"
        f"➡️ <b>Yangi ijrochi:</b> {new_worker_name}\n"
        f"────────────────────\n"
        f"<i>Sizdan bu vazifa olindi.</i>"
    )
    try:
        if callback.message.caption:
            await callback.message.edit_caption(caption=done_reassign_text, parse_mode="HTML")
        else:
            await callback.message.edit_text(done_reassign_text, parse_mode="HTML")
    except Exception:
        pass

    await callback.answer(f"Vazifa {new_worker_name}ga o'tkazildi!", show_alert=True)

    # 3. Send task to the NEW employee
    now_str = get_tashkent_str()
    new_worker_msg = (
        f"🔔 <b>SIZGA VAZIFA O'TKAZILDI #{task_id}!</b>\n"
        f"────────────────────\n"
        f"📝 <b>Vazifa:</b> {task['title']}\n"
        f"👤 <b>Kimdan o'tkazildi:</b> {old_worker_name}\n"
        f"👑 <b>Boshlang'ich rahbar:</b> {creator_name}\n"
        f"⏰ <b>Vaqt:</b> {now_str}\n"
        f"────────────────────\n"
        f"Vazifani bajargach '✅ Bajarildi' tugmasini bosing:"
    )

    if new_emp["telegram_id"]:
        try:
            if task["file_id"] and task["file_type"] == "document":
                await bot.send_document(
                    chat_id=new_emp["telegram_id"],
                    document=task["file_id"],
                    caption=new_worker_msg,
                    reply_markup=get_task_actions_keyboard(task_id),
                    parse_mode="HTML"
                )
            elif task["file_id"] and task["file_type"] == "photo":
                await bot.send_photo(
                    chat_id=new_emp["telegram_id"],
                    photo=task["file_id"],
                    caption=new_worker_msg,
                    reply_markup=get_task_actions_keyboard(task_id),
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    chat_id=new_emp["telegram_id"],
                    text=new_worker_msg,
                    reply_markup=get_task_actions_keyboard(task_id),
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"Yangi xodimga yuborishda xato: {e}")

    # 4. Notify the Creator / Admin
    if creator_id:
        admin_alert = (
            f"🔄 <b>Vazifa boshqa xodimga o'tkazildi!</b>\n"
            f"────────────────────\n"
            f"📌 <b>Vazifa #{task_id}:</b> {task['title']}\n"
            f"👤 <b>Avvalgi ijrochi:</b> {old_worker_name}\n"
            f"➡️ <b>Yangi ijrochi:</b> {new_worker_name}\n"
            f"⏱ <b>Vaqt:</b> {now_str}\n"
            f"────────────────────"
        )
        try:
            await bot.send_message(chat_id=creator_id, text=admin_alert, parse_mode="HTML")
        except Exception:
            pass

    # 5. Notify the Group
    group_id = await get_group_id()
    if group_id:
        group_alert = (
            f"🔄 <b>VAZIFA QAYTA TAYINLANDI</b>\n"
            f"────────────────────\n"
            f"📝 <b>Vazifa:</b> {task['title']}\n"
            f"👤 <b>Avvalgi ijrochi:</b> {old_worker_name}\n"
            f"➡️ <b>Yangi ijrochi:</b> {new_worker_name}\n"
            f"────────────────────\n"
            f"ℹ️ <i>Ta'minot bo'limi nazorati</i>"
        )
        try:
            await bot.send_message(chat_id=group_id, text=group_alert, parse_mode="HTML")
        except Exception:
            pass

@router.callback_query(F.data == "cancel_reassign")
async def cancel_reassign(callback: CallbackQuery):
    await callback.answer("Bekor qilindi")
    await callback.message.delete()

@router.message(F.text == "📋 Mening vazifalarim")
async def show_my_tasks(message: Message, bot: Bot):
    user_id = message.from_user.id
    emp = await get_employee_by_telegram_id(user_id)

    if not emp:
        await message.answer("⚠️ Siz hali xodim sifatida bog'lanmagansiz. /start buyrug'ini yuboring.")
        return

    tasks = await get_employee_tasks(emp["id"], active_only=True)

    if not tasks:
        await message.answer("🎉 Hozircha sizda faol vazifalar yo'q. Hammasi bajarilgan!")
        return

    await message.answer(f"📋 <b>Sizning faol vazifalaringiz ({len(tasks)} ta):</b>", parse_mode="HTML")
    for t in tasks:
        status_text = "⏳ Jarayonda" if t["status"] == "in_progress" else "🔴 Kutilmoqda"
        creator = t["creator_name"] or "Rahbar"
        msg = (
            f"📌 <b>Vazifa #{t['id']}</b>\n"
            f"📝 <b>Matn:</b> {t['title']}\n"
            f"👑 <b>Topshirdi:</b> {creator}\n"
            f"Holat: <i>{status_text}</i>\n"
            f"📅 Berilgan sana: <i>{t['created_at']}</i>"
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
            await message.answer(msg, reply_markup=get_task_actions_keyboard(t["id"]), parse_mode="HTML")
