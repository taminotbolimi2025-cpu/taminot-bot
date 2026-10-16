from aiogram.fsm.state import State, StatesGroup

class TaskCreationStates(StatesGroup):
    waiting_for_worker = State()
    waiting_for_task_text = State()
