from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

def get_admin_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Yangi vazifa berish"), KeyboardButton(text="📋 Mening vazifalarim")],
            [KeyboardButton(text="📋 Vazifalar nazorati"), KeyboardButton(text="🗑 Vazifani o'chirish")],
            [KeyboardButton(text="👥 Xodimlar ro'yxati"), KeyboardButton(text="⚙️ Guruhni sozlash")]
        ],
        resize_keyboard=True
    )


def get_worker_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Mening vazifalarim")],
            [KeyboardButton(text="ℹ️ Bot haqida")]
        ],
        resize_keyboard=True
    )

def get_assign_employee_keyboard(employees) -> InlineKeyboardMarkup:
    builder = []
    for emp in employees:
        status_dot = "🟢" if emp["telegram_id"] else "⚪️"
        text = f"{status_dot} {emp['full_name']}"
        builder.append([InlineKeyboardButton(text=text, callback_data=f"assign_emp:{emp['id']}")])
    
    builder.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_task_creation")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_file_comment_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Izohsiz davom etish", callback_data="skip_file_comment")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_task_creation")]
        ]
    )

def get_deadline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Bugun 18:00 gacha", callback_data="deadline_btn:today"),
                InlineKeyboardButton(text="📅 Ertaga 18:00 gacha", callback_data="deadline_btn:tomorrow")
            ],
            [
                InlineKeyboardButton(text="📅 2 kun muddat", callback_data="deadline_btn:2days"),
                InlineKeyboardButton(text="📅 1 hafta muddat", callback_data="deadline_btn:1week")
            ],
            [
                InlineKeyboardButton(text="✍️ Boshqa sana kiritish", callback_data="deadline_btn:custom"),
                InlineKeyboardButton(text="⏩ Muddatsiz", callback_data="deadline_btn:none")
            ],
            [
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_task_creation")
            ]
        ]
    )

def get_custom_deadline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_task_creation")]
        ]
    )


def get_bind_employee_keyboard(employees) -> InlineKeyboardMarkup:
    builder = []
    for emp in employees:
        status_note = " (✅ Ulangan)" if emp["telegram_id"] else ""
        text = f"👤 {emp['full_name']}{status_note}"
        builder.append([InlineKeyboardButton(text=text, callback_data=f"bind_me:{emp['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_task_actions_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"task_done:{task_id}"),
                InlineKeyboardButton(text="⏳ Jarayonda", callback_data=f"task_progress:{task_id}")
            ],
            [
                InlineKeyboardButton(text="🔄 Boshqa xodimga o'tkazish", callback_data=f"task_reassign:{task_id}")
            ]
        ]
    )

def get_completion_report_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏩ Faylsiz / Faqat matn bilan tasdiqlash", callback_data=f"skip_report:{task_id}")
            ],
            [
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_completion:{task_id}")
            ]
        ]
    )

def get_reassign_employee_keyboard(task_id: int, employees, current_emp_id: int = None) -> InlineKeyboardMarkup:
    builder = []
    for emp in employees:
        if current_emp_id and emp["id"] == current_emp_id:
            continue
        status_dot = "🟢" if emp["telegram_id"] else "⚪️"
        text = f"{status_dot} {emp['full_name']}"
        builder.append([InlineKeyboardButton(text=text, callback_data=f"do_reassign:{task_id}:{emp['id']}")])
    builder.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_reassign")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_task_filter_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔴 Faol vazifalar", callback_data="filter_tasks:active"),
                InlineKeyboardButton(text="🟢 Bajarilganlar", callback_data="filter_tasks:done")
            ],
            [
                InlineKeyboardButton(text="📋 Barcha vazifalar", callback_data="filter_tasks:all")
            ],
            [
                InlineKeyboardButton(text="🗑 Vazifani o'chirish", callback_data="start_delete_task")
            ]
        ]
    )

def get_delete_tasks_keyboard(tasks) -> InlineKeyboardMarkup:
    builder = []
    for t in tasks:
        worker = t["employee_name"] or "Xodim"
        raw_title = t["title"] or "Vazifa"
        title_snippet = (raw_title[:20] + "...") if len(raw_title) > 23 else raw_title
        status_icon = "⏳" if t["status"] == "in_progress" else ("✅" if t["status"] == "done" else "🔴")
        text = f"{status_icon} #{t['id']} {title_snippet} ({worker})"
        builder.append([InlineKeyboardButton(text=text, callback_data=f"ask_delete_task:{t['id']}")])
    builder.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_delete_task")])
    return InlineKeyboardMarkup(inline_keyboard=builder)

def get_confirm_delete_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Ha, butunlay o'chirilsin", callback_data=f"confirm_delete_task:{task_id}")
            ],
            [
                InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="cancel_delete_task")
            ]
        ]
    )

