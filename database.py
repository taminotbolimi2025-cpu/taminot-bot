import aiosqlite
from datetime import datetime
from config import DB_PATH, ADMIN_IDS, DEFAULT_GROUP_ID

INITIAL_EMPLOYEES = [
    "Zubayr Anvarov",
    "Abdulhafiz Mirzamurodov",
    "Abdurahmon Asrarov",
    "Muhammadamin Nabijonov"
]

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Employees table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL UNIQUE,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Tasks table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                employee_id INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                status TEXT DEFAULT 'pending', -- pending, in_progress, done
                created_at TEXT,
                completed_at TEXT,
                file_id TEXT,
                file_type TEXT,
                completion_file_id TEXT,
                completion_file_type TEXT,
                completion_comment TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees (id)
            )
        """)

        # Ensure columns exist if table was already created
        cursor = await db.execute("PRAGMA table_info(tasks)")
        cols = [row[1] for row in await cursor.fetchall()]
        if "file_id" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN file_id TEXT")
        if "file_type" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN file_type TEXT")
        if "completion_file_id" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN completion_file_id TEXT")
        if "completion_file_type" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN completion_file_type TEXT")
        if "completion_comment" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN completion_comment TEXT")

        # Settings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()

        # Seed initial employees
        for name in INITIAL_EMPLOYEES:
            await db.execute(
                "INSERT OR IGNORE INTO employees (full_name, is_active) VALUES (?, 1)",
                (name,)
            )
        await db.commit()

        # If DEFAULT_GROUP_ID is set in .env
        if DEFAULT_GROUP_ID:
            row = await (await db.execute("SELECT value FROM settings WHERE key = 'group_id'")).fetchone()
            if not row:
                await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('group_id', ?)", (str(DEFAULT_GROUP_ID),))
                await db.commit()

async def get_all_employees():
    """Returns all active employees"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM employees WHERE is_active = 1 ORDER BY id ASC")
        return await cursor.fetchall()

async def get_employee_by_id(emp_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM employees WHERE id = ?", (emp_id,))
        return await cursor.fetchone()

async def get_employee_by_telegram_id(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM employees WHERE telegram_id = ?", (telegram_id,))
        return await cursor.fetchone()

async def bind_employee(emp_id: int, telegram_id: int, username: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        # Unbind if already bound anywhere else
        await db.execute("UPDATE employees SET telegram_id = NULL WHERE telegram_id = ?", (telegram_id,))
        await db.execute(
            "UPDATE employees SET telegram_id = ?, username = ? WHERE id = ?",
            (telegram_id, username, emp_id)
        )
        await db.commit()

async def add_employee(full_name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO employees (full_name, is_active) VALUES (?, 1)",
            (full_name,)
        )
        await db.commit()
        return cursor.lastrowid

async def create_task(title: str, description: str, employee_id: int, created_by: int, file_id: str = None, file_type: str = None) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO tasks (title, description, employee_id, created_by, status, created_at, file_id, file_type)
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (title, description, employee_id, created_by, now, file_id, file_type)
        )
        await db.commit()
        return cursor.lastrowid

async def get_task(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT t.*, 
                   e.full_name AS employee_name, 
                   e.telegram_id AS employee_telegram_id,
                   e.username AS employee_username,
                   c.full_name AS creator_name
            FROM tasks t
            LEFT JOIN employees e ON t.employee_id = e.id
            LEFT JOIN employees c ON t.created_by = c.telegram_id
            WHERE t.id = ?
            """,
            (task_id,)
        )
        return await cursor.fetchone()

async def update_task_status(task_id: int, status: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "done" else None
    async with aiosqlite.connect(DB_PATH) as db:
        if status == "done":
            await db.execute(
                "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
                (status, now, task_id)
            )
        else:
            await db.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (status, task_id)
            )
        await db.commit()

async def complete_task(task_id: int, comment: str = "", file_id: str = None, file_type: str = None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE tasks 
            SET status = 'done', 
                completed_at = ?, 
                completion_comment = ?, 
                completion_file_id = ?, 
                completion_file_type = ? 
            WHERE id = ?
            """,
            (now, comment, file_id, file_type, task_id)
        )
        await db.commit()

async def reassign_task(task_id: int, new_employee_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tasks SET employee_id = ? WHERE id = ?",
            (new_employee_id, task_id)
        )
        await db.commit()

async def get_employee_tasks(employee_id: int, active_only: bool = True):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if active_only:
            query = """
                SELECT t.*, c.full_name AS creator_name 
                FROM tasks t 
                LEFT JOIN employees c ON t.created_by = c.telegram_id
                WHERE t.employee_id = ? AND t.status IN ('pending', 'in_progress') 
                ORDER BY t.id DESC
            """
        else:
            query = """
                SELECT t.*, c.full_name AS creator_name 
                FROM tasks t 
                LEFT JOIN employees c ON t.created_by = c.telegram_id
                WHERE t.employee_id = ? 
                ORDER BY t.id DESC LIMIT 15
            """
        cursor = await db.execute(query, (employee_id,))
        return await cursor.fetchall()

async def get_all_tasks(filter_type: str = "active", limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if filter_type == "active":
            query = """
                SELECT t.*, 
                       e.full_name AS employee_name,
                       c.full_name AS creator_name
                FROM tasks t 
                LEFT JOIN employees e ON t.employee_id = e.id 
                LEFT JOIN employees c ON t.created_by = c.telegram_id
                WHERE t.status IN ('pending', 'in_progress') 
                ORDER BY t.id DESC LIMIT ?
            """
        elif filter_type == "done":
            query = """
                SELECT t.*, 
                       e.full_name AS employee_name,
                       c.full_name AS creator_name
                FROM tasks t 
                LEFT JOIN employees e ON t.employee_id = e.id 
                LEFT JOIN employees c ON t.created_by = c.telegram_id
                WHERE t.status = 'done' 
                ORDER BY t.id DESC LIMIT ?
            """
        else:
            query = """
                SELECT t.*, 
                       e.full_name AS employee_name,
                       c.full_name AS creator_name
                FROM tasks t 
                LEFT JOIN employees e ON t.employee_id = e.id 
                LEFT JOIN employees c ON t.created_by = c.telegram_id
                ORDER BY t.id DESC LIMIT ?
            """
        cursor = await db.execute(query, (limit,))
        return await cursor.fetchall()

async def set_group_id(chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('group_id', ?)",
            (str(chat_id),)
        )
        await db.commit()

async def get_group_id():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = 'group_id'")
        row = await cursor.fetchone()
        if row and row[0]:
            try:
                return int(row[0])
            except ValueError:
                return None
        return None
