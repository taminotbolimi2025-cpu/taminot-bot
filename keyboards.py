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
            [KeyboardButton(text="📋 Vazifalar nazorati"), KeyboardButton(text="👥 Xodimlar ro'yxati")],
            [KeyboardButton(text="⚙️ Guruhni sozlash")]
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
            ]
        ]
    )
