from aiogram.fsm.state import State, StatesGroup

class TaskCreationStates(StatesGroup):
    waiting_for_worker = State()
    waiting_for_task_text = State()
    waiting_for_file_comment = State()
    waiting_for_deadline = State()
    waiting_for_custom_deadline = State()

class TaskCompletionStates(StatesGroup):
    waiting_for_report = State()

