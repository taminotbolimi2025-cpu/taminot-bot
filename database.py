import logging
import aiosqlite
from config import DB_PATH, DATABASE_URL, DEFAULT_GROUP_ID, get_tashkent_db_str

logger = logging.getLogger("taminot_database")

# Pre-seeded employees with their known Telegram bindings
INITIAL_EMPLOYEES = [
    ("Zubayr Anvarov", 928391586, "Zen1n_Sel1m"),
    ("Abdulhafiz Mirzamurodov", None, None),
    ("Abdurahmon Asrarov", 6007250614, "trk030"),
    ("Muhammadamin Nabijonov", 2106208675, "AbuSofiya_M")
]

_pg_pool = None

async def init_db():
    global _pg_pool
    # 1. Try to connect to PostgreSQL if DATABASE_URL is set
    if DATABASE_URL:
        try:
            import asyncpg
            logger.info("PostgreSQL bulut bazasiga ulanish tekshirilmoqda...")
            _pg_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=15,
                timeout=5
            )
            logger.info("✅ PostgreSQL bulutli ma'lumotlar bazasiga muvaffaqiyatli ulandi! (Render Postgres)")
            await _init_postgres()
            return
        except Exception as e:
            logger.warning(f"PostgreSQL ulanmadi ({e}). SQLite zaxira rejimiga o'tilmoqda.")
            _pg_pool = None

    # 2. Fallback to SQLite (e.g. for local offline testing)
    await _init_sqlite()

async def _init_postgres():
    async with _pg_pool.acquire() as conn:
        # Employees table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL UNIQUE,
                telegram_id BIGINT UNIQUE,
                username TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Tasks table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                employee_id INTEGER NOT NULL REFERENCES employees (id),
                created_by BIGINT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                completed_at TEXT,
                file_id TEXT,
                file_type TEXT,
                completion_file_id TEXT,
                completion_file_type TEXT,
                completion_comment TEXT,
                deadline TEXT,
                deadline_date TEXT,
                deadline_ts TEXT,
                reminder_sent INTEGER DEFAULT 0
            )
        """)

        # Settings table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Seed initial employees
        for name, tg_id, username in INITIAL_EMPLOYEES:
            await conn.execute("""
                INSERT INTO employees (full_name, telegram_id, username, is_active)
                VALUES ($1, $2, $3, 1)
                ON CONFLICT (full_name) DO UPDATE SET
                    telegram_id = COALESCE(employees.telegram_id, EXCLUDED.telegram_id),
                    username = COALESCE(employees.username, EXCLUDED.username)
            """, name, tg_id, username)

        # Seed default group if set
        if DEFAULT_GROUP_ID:
            row = await conn.fetchrow("SELECT value FROM settings WHERE key = 'group_id'")
            if not row:
                await conn.execute(
                    "INSERT INTO settings (key, value) VALUES ('group_id', $1) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                    str(DEFAULT_GROUP_ID)
                )

async def _init_sqlite():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL UNIQUE,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                employee_id INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                completed_at TEXT,
                file_id TEXT,
                file_type TEXT,
                completion_file_id TEXT,
                completion_file_type TEXT,
                completion_comment TEXT,
                deadline TEXT,
                deadline_date TEXT,
                deadline_ts TEXT,
                reminder_sent INTEGER DEFAULT 0,
                FOREIGN KEY (employee_id) REFERENCES employees (id)
            )
        """)

        cursor = await db.execute("PRAGMA table_info(tasks)")
        cols = [row[1] for row in await cursor.fetchall()]
        if "deadline" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN deadline TEXT")
        if "deadline_date" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN deadline_date TEXT")
        if "deadline_ts" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN deadline_ts TEXT")
        if "reminder_sent" not in cols:
            await db.execute("ALTER TABLE tasks ADD COLUMN reminder_sent INTEGER DEFAULT 0")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()

        for name, tg_id, username in INITIAL_EMPLOYEES:
            await db.execute(
                "INSERT OR IGNORE INTO employees (full_name, telegram_id, username, is_active) VALUES (?, ?, ?, 1)",
                (name, tg_id, username)
            )
        await db.commit()

        if DEFAULT_GROUP_ID:
            row = await (await db.execute("SELECT value FROM settings WHERE key = 'group_id'")).fetchone()
            if not row:
                await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('group_id', ?)", (str(DEFAULT_GROUP_ID),))
                await db.commit()

# --- Functions ---

async def get_all_employees():
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM employees WHERE is_active = 1 ORDER BY id ASC")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM employees WHERE is_active = 1 ORDER BY id ASC")
        return await cursor.fetchall()

async def get_employee_by_id(emp_id: int):
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM employees WHERE id = $1", emp_id)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM employees WHERE id = ?", (emp_id,))
        return await cursor.fetchone()

async def get_employee_by_telegram_id(telegram_id: int):
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM employees WHERE telegram_id = $1", telegram_id)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM employees WHERE telegram_id = ?", (telegram_id,))
        return await cursor.fetchone()

async def bind_employee(emp_id: int, telegram_id: int, username: str = None):
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            await conn.execute("UPDATE employees SET telegram_id = NULL WHERE telegram_id = $1", telegram_id)
            await conn.execute("UPDATE employees SET telegram_id = $1, username = $2 WHERE id = $3", telegram_id, username, emp_id)
            return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE employees SET telegram_id = NULL WHERE telegram_id = ?", (telegram_id,))
        await db.execute("UPDATE employees SET telegram_id = ?, username = ? WHERE id = ?", (telegram_id, username, emp_id))
        await db.commit()

async def add_employee(full_name: str) -> int:
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            return await conn.fetchval("INSERT INTO employees (full_name, is_active) VALUES ($1, 1) RETURNING id", full_name)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO employees (full_name, is_active) VALUES (?, 1)", (full_name,))
        await db.commit()
        return cursor.lastrowid

async def create_task(
    title: str,
    description: str,
    employee_id: int,
    created_by: int,
    file_id: str = None,
    file_type: str = None,
    deadline: str = None,
    deadline_date: str = None,
    deadline_ts: str = None
) -> int:
    now = get_tashkent_db_str()
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO tasks (
                    title, description, employee_id, created_by, status, created_at,
                    file_id, file_type, deadline, deadline_date, deadline_ts, reminder_sent
                )
                VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7, $8, $9, $10, 0)
                RETURNING id
                """,
                title, description, employee_id, created_by, now, file_id, file_type, deadline, deadline_date, deadline_ts
            )
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO tasks (
                title, description, employee_id, created_by, status, created_at,
                file_id, file_type, deadline, deadline_date, deadline_ts, reminder_sent
            )
            VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, 0)
            """,
            (title, description, employee_id, created_by, now, file_id, file_type, deadline, deadline_date, deadline_ts)
        )
        await db.commit()
        return cursor.lastrowid

async def get_tasks_due_for_reminder(current_date_str: str):
    query = """
        SELECT t.*, 
               e.full_name AS employee_name, 
               e.telegram_id AS employee_telegram_id,
               c.full_name AS creator_name
        FROM tasks t
        LEFT JOIN employees e ON t.employee_id = e.id
        LEFT JOIN employees c ON t.created_by = c.telegram_id
        WHERE t.status IN ('pending', 'in_progress')
          AND t.deadline_date IS NOT NULL
          AND t.deadline_date <= {p1}
          AND t.reminder_sent = 0
        ORDER BY t.id ASC
    """
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            return await conn.fetch(query.format(p1="$1"), current_date_str)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query.format(p1="?"), (current_date_str,))
        return await cursor.fetchall()

async def get_tasks_overdue(current_ts_str: str):
    query = """
        SELECT t.*, 
               e.full_name AS employee_name, 
               e.telegram_id AS employee_telegram_id,
               c.full_name AS creator_name
        FROM tasks t
        LEFT JOIN employees e ON t.employee_id = e.id
        LEFT JOIN employees c ON t.created_by = c.telegram_id
        WHERE t.status IN ('pending', 'in_progress')
          AND t.deadline_ts IS NOT NULL
          AND t.deadline_ts < {p1}
          AND t.reminder_sent = 1
        ORDER BY t.id ASC
    """
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            return await conn.fetch(query.format(p1="$1"), current_ts_str)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query.format(p1="?"), (current_ts_str,))
        return await cursor.fetchall()

async def mark_task_reminder_sent(task_id: int, level: int = 1):
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            await conn.execute("UPDATE tasks SET reminder_sent = $1 WHERE id = $2", level, task_id)
            return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET reminder_sent = ? WHERE id = ?", (level, task_id))
        await db.commit()

async def get_task(task_id: int):
    query = """
        SELECT t.*, 
               e.full_name AS employee_name, 
               e.telegram_id AS employee_telegram_id,
               e.username AS employee_username,
               c.full_name AS creator_name
        FROM tasks t
        LEFT JOIN employees e ON t.employee_id = e.id
        LEFT JOIN employees c ON t.created_by = c.telegram_id
        WHERE t.id = {p1}
    """
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            return await conn.fetchrow(query.format(p1="$1"), task_id)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query.format(p1="?"), (task_id,))
        return await cursor.fetchone()

async def update_task_status(task_id: int, status: str):
    now = get_tashkent_db_str() if status == "done" else None
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            if status == "done":
                await conn.execute("UPDATE tasks SET status = $1, completed_at = $2 WHERE id = $3", status, now, task_id)
            else:
                await conn.execute("UPDATE tasks SET status = $1 WHERE id = $2", status, task_id)
            return
    async with aiosqlite.connect(DB_PATH) as db:
        if status == "done":
            await db.execute("UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?", (status, now, task_id))
        else:
            await db.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        await db.commit()

async def complete_task(task_id: int, comment: str = "", file_id: str = None, file_type: str = None):
    now = get_tashkent_db_str()
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE tasks 
                SET status = 'done', 
                    completed_at = $1, 
                    completion_comment = $2, 
                    completion_file_id = $3, 
                    completion_file_type = $4 
                WHERE id = $5
                """,
                now, comment, file_id, file_type, task_id
            )
            return
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
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            await conn.execute("UPDATE tasks SET employee_id = $1 WHERE id = $2", new_employee_id, task_id)
            return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET employee_id = ? WHERE id = ?", (new_employee_id, task_id))
        await db.commit()

async def delete_task(task_id: int):
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            await conn.execute("DELETE FROM tasks WHERE id = $1", task_id)
            return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()

async def get_employee_tasks(employee_id: int, active_only: bool = True):
    if active_only:
        query = """
            SELECT t.*, c.full_name AS creator_name 
            FROM tasks t 
            LEFT JOIN employees c ON t.created_by = c.telegram_id
            WHERE t.employee_id = {p1} AND t.status IN ('pending', 'in_progress') 
            ORDER BY t.id DESC
        """
    else:
        query = """
            SELECT t.*, c.full_name AS creator_name 
            FROM tasks t 
            LEFT JOIN employees c ON t.created_by = c.telegram_id
            WHERE t.employee_id = {p1} 
            ORDER BY t.id DESC LIMIT 15
        """
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            return await conn.fetch(query.format(p1="$1"), employee_id)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query.format(p1="?"), (employee_id,))
        return await cursor.fetchall()

async def get_all_tasks(filter_type: str = "active", limit: int = 20):
    if filter_type == "active":
        query = """
            SELECT t.*, 
                   e.full_name AS employee_name,
                   c.full_name AS creator_name
            FROM tasks t 
            LEFT JOIN employees e ON t.employee_id = e.id 
            LEFT JOIN employees c ON t.created_by = c.telegram_id
            WHERE t.status IN ('pending', 'in_progress') 
            ORDER BY t.id DESC LIMIT {p1}
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
            ORDER BY t.id DESC LIMIT {p1}
        """
    else:
        query = """
            SELECT t.*, 
                   e.full_name AS employee_name,
                   c.full_name AS creator_name
            FROM tasks t 
            LEFT JOIN employees e ON t.employee_id = e.id 
            LEFT JOIN employees c ON t.created_by = c.telegram_id
            ORDER BY t.id DESC LIMIT {p1}
        """
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            return await conn.fetch(query.format(p1="$1"), limit)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query.format(p1="?"), (limit,))
        return await cursor.fetchall()

async def set_group_id(chat_id: int):
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO settings (key, value) VALUES ('group_id', $1) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                str(chat_id)
            )
            return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('group_id', ?)", (str(chat_id),))
        await db.commit()

async def get_group_id():
    if _pg_pool:
        async with _pg_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT value FROM settings WHERE key = 'group_id'")
            if row and row["value"]:
                try:
                    return int(row["value"])
                except ValueError:
                    return None
            return None
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = 'group_id'")
        row = await cursor.fetchone()
        if row and row[0]:
            try:
                return int(row[0])
            except ValueError:
                return None
        return None
