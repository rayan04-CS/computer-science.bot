# CS Computer Science Student Bot
# Telegram Library Bot

import asyncio
import os
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


# =========================
# SETTINGS
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

DB_PATH = os.getenv("DB_PATH", "cs_library.db")


# =========================
# BOT
# =========================

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# =========================
# DATABASE
# =========================

async def db():
    return await aiosqlite.connect(DB_PATH)


async def init_db():
    async with await db() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                units INTEGER DEFAULT 0,
                year TEXT DEFAULT '',
                semester TEXT DEFAULT '',
                prerequisite TEXT DEFAULT ''
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                display_name TEXT NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                FOREIGN KEY(subject_id) REFERENCES subjects(id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        await conn.commit()


# =========================
# KEYBOARDS
# =========================

def main_menu(user_id: int):

    buttons = [
        [
            InlineKeyboardButton(
                text="📚 المواد",
                callback_data="subjects"
            )
        ],
        [
            InlineKeyboardButton(
                text="🌳 شجرة المواد",
                callback_data="tree"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔍 البحث عن مادة",
                callback_data="search"
            )
        ],
        [
            InlineKeyboardButton(
                text="ℹ️ عن المكتبة",
                callback_data="about"
            )
        ]
    ]

    if user_id in ADMIN_IDS:
        buttons.append([
            InlineKeyboardButton(
                text="👑 لوحة الإدارة",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 رجوع",
                    callback_data="home"
                )
            ]
        ]
    )


# =========================
# START
# =========================

@dp.message(Command("start"))
async def start(message: Message):

    text = (
        "🎓 Computer Science Student Bot\n\n"
        "مكتبة قسم علوم الحاسوب 👩🏻‍💻\n\n"
        "اختار من القائمة:"
    )

    await message.answer(
        text,
        reply_markup=main_menu(message.from_user.id)
    )


# =========================
# HOME
# =========================

@dp.callback_query(F.data == "home")
async def home(callback: CallbackQuery):

    await callback.message.edit_text(
        "🎓 Computer Science Student Bot\n\n"
        "مكتبة قسم علوم الحاسوب 👩🏻‍💻\n\n"
        "اختار من القائمة:",
        reply_markup=main_menu(callback.from_user.id)
    )

    await callback.answer()


# =========================
# SUBJECTS
# =========================

@dp.callback_query(F.data == "subjects")
async def subjects(callback: CallbackQuery):

    async with await db() as conn:

        cursor = await conn.execute("""
            SELECT id, name, units, year, semester
            FROM subjects
            ORDER BY year, id
        """)

        rows = await cursor.fetchall()

    buttons = []

    for subject_id, name, units, year, semester in rows:

        buttons.append([
            InlineKeyboardButton(
                text=f"📘 {name}",
                callback_data=f"subject:{subject_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 رجوع",
            callback_data="home"
        )
    ])

    if not rows:

        await callback.message.edit_text(
            "📚 المواد\n\n"
            "ما فيش مواد مضافة حالياً.",
            reply_markup=back_button()
        )

    else:

        await callback.message.edit_text(
            "📚 مواد قسم علوم الحاسوب\n\n"
            "اختار المادة:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=buttons
            )
        )

    await callback.answer()


# =========================
# SUBJECT DETAILS
# =========================

@dp.callback_query(F.data.startswith("subject:"))
async def subject_details(callback: CallbackQuery):

    subject_id = int(callback.data.split(":")[1])

    async with await db() as conn:

        cursor = await conn.execute("""
            SELECT name, units, year, semester, prerequisite
            FROM subjects
            WHERE id = ?
        """, (subject_id,))

        subject = await cursor.fetchone()

    if not subject:

        await callback.answer(
            "المادة مش موجودة.",
            show_alert=True
        )
        return

    name, units, year, semester, prerequisite = subject

    text = (
        f"📘 {name}\n\n"
        f"🔢 الوحدات: {units}\n"
        f"📅 السنة: {year}\n"
        f"📚 الفصل: {semester}\n"
        f"🔗 المتطلب السابق: {prerequisite or 'لا يوجد'}\n\n"
        "اختار القسم:"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 المراجع والكتب",
                    callback_data=f"cat:{subject_id}:books"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 الشيتات",
                    callback_data=f"cat:{subject_id}:sheets"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 الأسئلة",
                    callback_data=f"cat:{subject_id}:questions"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 رجوع",
                    callback_data="subjects"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard
    )

    await callback.answer()


# =========================
# CONTENT
# =========================

CATEGORY_NAMES = {
    "books": "📚 المراجع والكتب",
    "sheets": "📝 الشيتات",
    "questions": "📋 الأسئلة"
}


@dp.callback_query(F.data.startswith("cat:"))
async def show_category(callback: CallbackQuery):

    _, subject_id, category = callback.data.split(":")

    subject_id = int(subject_id)

    async with await db() as conn:

        cursor = await conn.execute("""
            SELECT id, display_name
            FROM contents
            WHERE subject_id = ?
            AND category = ?
            ORDER BY id
        """, (subject_id, category))

        rows = await cursor.fetchall()

        cursor = await conn.execute("""
            SELECT name
            FROM subjects
            WHERE id = ?
        """, (subject_id,))

        subject = await cursor.fetchone()

    if not subject:
        await callback.answer(
            "المادة مش موجودة.",
            show_alert=True
        )
        return

    buttons = []

    for content_id, display_name in rows:

        buttons.append([
            InlineKeyboardButton(
                text=f"📄 {display_name}",
                callback_data=f"file:{content_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 رجوع",
            callback_data=f"subject:{subject_id}"
        )
    ])

    text = (
        f"{CATEGORY_NAMES.get(category, '📁 المحتوى')}\n\n"
        f"📘 المادة: {subject[0]}\n\n"
        "اختار الملف:"
    )

    if not rows:
        text += "\nما فيش ملفات مضافة حالياً."

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


# =========================
# SEND FILE
# =========================

@dp.callback_query(F.data.startswith("file:"))
async def send_file(callback: CallbackQuery):

    content_id = int(callback.data.split(":")[1])

    async with await db() as conn:

        cursor = await conn.execute("""
            SELECT display_name, file_id, file_type
            FROM contents
            WHERE id = ?
        """, (content_id,))

        content = await cursor.fetchone()

    if not content:

        await callback.answer(
            "الملف مش موجود.",
            show_alert=True
        )
        return

    display_name, file_id, file_type = content

    try:

        if file_type == "document":
            await callback.message.answer_document(
                file_id,
                caption=f"📄 {display_name}"
            )

        elif file_type == "photo":
            await callback.message.answer_photo(
                file_id,
                caption=f"🖼️ {display_name}"
            )

        elif file_type == "video":
            await callback.message.answer_video(
                file_id,
                caption=f"🎬 {display_name}"
            )

        elif file_type == "audio":
            await callback.message.answer_audio(
                file_id,
                caption=f"🎵 {display_name}"
            )

        elif file_type == "voice":
            await callback.message.answer_voice(
                file_id
            )

        await callback.answer()

    except Exception:

        await callback.answer(
            "صار خطأ في إرسال الملف.",
            show_alert=True
        )


# =========================
# TREE
# =========================

@dp.callback_query(F.data == "tree")
async def tree(callback: CallbackQuery):

    async with await db() as conn:

        cursor = await conn.execute("""
            SELECT value
            FROM settings
            WHERE key = 'tree_file'
        """)

        row = await cursor.fetchone()

    if not row:

        await callback.message.edit_text(
            "🌳 شجرة المواد\n\n"
            "شجرة المواد مش مضافة حالياً.",
            reply_markup=back_button()
        )

        await callback.answer()
        return

    await callback.message.answer_document(
        row[0],
        caption="🌳 شجرة مواد قسم علوم الحاسوب"
    )

    await callback.answer()


# =========================
# ABOUT
# =========================

@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):

    await callback.message.edit_text(
        "ℹ️ عن المكتبة\n\n"
        "🎓 Computer Science Student Bot\n\n"
        "مكتبة إلكترونية لطلبة قسم علوم الحاسوب.\n\n"
        "تقدر من خلالها توصل إلى:\n"
        "📚 المراجع والكتب\n"
        "📝 الشيتات\n"
        "📋 الأسئلة\n"
        "🌳 شجرة المواد",
        reply_markup=back_button()
    )

    await callback.answer()


# =========================
# SEARCH
# =========================

class SearchState(StatesGroup):
    waiting = State()


@dp.callback_query(F.data == "search")
async def search_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await state.set_state(SearchState.waiting)

    await callback.message.answer(
        "🔍 البحث عن مادة\n\n"
        "اكتب اسم المادة:"
    )

    await callback.answer()


@dp.message(SearchState.waiting)
async def search_subject(
    message: Message,
    state: FSMContext
):

    query = message.text.strip()

    async with await db() as conn:

        cursor = await conn.execute("""
            SELECT id, name
            FROM subjects
            WHERE name LIKE ?
            ORDER BY name
        """, (f"%{query}%",))

        rows = await cursor.fetchall()

    await state.clear()

    if not rows:

        await message.answer(
            "❌ ما لقيتش مادة بهذا الاسم.",
            reply_markup=main_menu(message.from_user.id)
        )
        return

    buttons = []

    for subject_id, name in rows:

        buttons.append([
            InlineKeyboardButton(
                text=f"📘 {name}",
                callback_data=f"subject:{subject_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 الرئيسية",
            callback_data="home"
        )
    ])

    await message.answer(
        "🔍 نتائج البحث:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )


# =========================================================
# ADMIN
# =========================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 إدارة المواد",
                    callback_data="admin_subjects"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📤 إضافة محتوى",
                    callback_data="admin_add_content"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ حذف محتوى",
                    callback_data="admin_delete_content"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌳 شجرة المواد",
                    callback_data="admin_tree"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 الرئيسية",
                    callback_data="home"
                )
            ]
        ]
    )


@dp.callback_query(F.data == "admin")
async def admin(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "مش مسموح.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        "👑 لوحة الإدارة\n\n"
        "اختار العملية:",
        reply_markup=admin_menu()
    )

    await callback.answer()


# =========================================================
# ADD SUBJECT
# =========================================================

class AddSubject(StatesGroup):
    name = State()
    units = State()
    year = State()
    semester = State()
    prerequisite = State()


@dp.callback_query(F.data == "admin_subjects")
async def admin_subjects(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer("مش مسموح.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ إضافة مادة",
                    callback_data="add_subject"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 عرض المواد",
                    callback_data="list_subjects"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 الإدارة",
                    callback_data="admin"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "📚 إدارة المواد",
        reply_markup=keyboard
    )

    await callback.answer()


@dp.callback_query(F.data == "add_subject")
async def add_subject_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):
        await callback.answer("مش مسموح.", show_alert=True)
        return

    await state.set_state(AddSubject.name)

    await callback.message.answer(
        "اكتب اسم المادة:"
    )

    await callback.answer()


@dp.message(AddSubject.name)
async def add_subject_name(
    message: Message,
    state: FSMContext
):

    await state.update_data(name=message.text.strip())
    await state.set_state(AddSubject.units)

    await message.answer(
        "اكتب عدد الوحدات:"
    )


@dp.message(AddSubject.units)
async def add_subject_units(
    message: Message,
    state: FSMContext
):

    if not message.text.isdigit():

        await message.answer(
            "اكتب عدد الوحدات كرقم فقط."
        )
        return

    await state.update_data(
        units=int(message.text)
    )

    await state.set_state(AddSubject.year)

    await message.answer(
        "اكتب السنة:"
    )


@dp.message(AddSubject.year)
async def add_subject_year(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        year=message.text.strip()
    )

    await state.set_state(AddSubject.semester)

    await message.answer(
        "اكتب الفصل:"
    )


@dp.message(AddSubject.semester)
async def add_subject_semester(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        semester=message.text.strip()
    )

    await state.set_state(AddSubject.prerequisite)

    await message.answer(
        "اكتب المتطلب السابق، أو اكتب: لا يوجد"
    )


@dp.message(AddSubject.prerequisite)
async def add_subject_finish(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    async with await db() as conn:

        await conn.execute("""
            INSERT INTO subjects
            (name, units, year, semester, prerequisite)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data["name"],
            data["units"],
            data["year"],
            data["semester"],
            message.text.strip()
        ))

        await conn.commit()

    await state.clear()

    await message.answer(
        "✅ تمت إضافة المادة بنجاح.",
        reply_markup=admin_menu()
    )


# =========================================================
# LIST SUBJECTS
# =========================================================

@dp.callback_query(F.data == "list_subjects")
async def list_subjects(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer("مش مسموح.", show_alert=True)
        return

    async with await db() as conn:

        cursor = await conn.execute("""
            SELECT id, name
            FROM subjects
            ORDER BY id
        """)

        rows = await cursor.fetchall()

    if not rows:

        text = "📋 ما فيش مواد مضافة."
    else:

        text = "📋 المواد الموجودة:\n\n"

        for index, (_, name) in enumerate(rows, 1):
            text += f"{index}. {name}\n"

    await callback.message.edit_text(
        text,
        reply_markup=back_button()
    )

    await callback.answer()


# =========================================================
# ADD CONTENT
# =========================================================

class AddContent(StatesGroup):
    subject = State()
    category = State()
    file = State()
    display_name = State()


@dp.callback_query(F.data == "admin_add_content")
async def add_content_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):
        await callback.answer("مش مسموح.", show_alert=True)
        return

    async with await db() as conn:

        cursor = await conn.execute("""
            SELECT id, name
            FROM subjects
            ORDER BY name
        """)

        rows = await cursor.fetchall()

    if not rows:

        await callback.answer(
            "أضف المواد أولاً.",
            show_alert=True
        )
        return

    buttons = []

    for subject_id, name in rows:

        buttons.append([
            InlineKeyboardButton(
                text=f"📘 {name}",
                callback_data=f"addcontent_subject:{subject_id}"
            )
        ])

    await callback.message.edit_text(
        "📤 إضافة محتوى\n\n"
        "اختار المادة:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("addcontent_subject:"))
async def add_content_subject(
    callback: CallbackQuery,
    state: FSMContext
):

    subject_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        subject_id=subject_id
    )

    await state.set_state(
        AddContent.category
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 المراجع والكتب",
                    callback_data="addcontent_category:books"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 الشيتات",
                    callback_data="addcontent_category:sheets"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 الأسئلة",
                    callback_data="addcontent_category:questions"
                )
            ]
        ]
    )

    await callback.message.edit_text(
        "اختار نوع المحتوى:",
        reply_markup=keyboard
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("addcontent_category:"))
async def add_content_category(
    callback: CallbackQuery,
    state: FSMContext
):

    category = callback.data.split(":")[1]

    await state.update_data(
        category=category
    )

    await state.set_state(
        AddContent.file
    )

    await callback.message.answer(
        "📤 ابعث الملف هنا.\n\n"
        "تقدر:\n"
        "• ترفع الملف مباشرة\n"
        "• أو تعمل Forward لملف موجود عندك في التليجرام"
    )

    await callback.answer()


@dp.message(AddContent.file)
async def add_content_file(
    message: Message,
    state: FSMContext
):

    file_id = None
    file_type = None

    if message.document:

        file_id = message.document.file_id
        file_type = "document"

    elif message.photo:

        file_id = message.photo[-1].file_id
        file_type = "photo"

    elif message.video:

        file_id = message.video.file_id
        file_type = "video"

    elif message.audio:

        file_id = message.audio.file_id
        file_type = "audio"

    elif message.voice:

        file_id = message.voice.file_id
        file_type = "voice"

    else:

        await message.answer(
            "❌ ابعث ملف أو اعمل Forward لملف."
        )
        return

    await state.update_data(
        file_id=file_id,
        file_type=file_type
    )

    await state.set_state(
        AddContent.display_name
    )

    await message.answer(
        "✏️ اكتب الاسم اللي تبي يظهر للطلاب:"
    )


@dp.message(AddContent.display_name)
async def save_content(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    async with await db() as conn:

        await conn.execute("""
            INSERT INTO contents
            (subject_id, category, display_name, file_id, file_type)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data["subject_id"],
            data["category"],
            message.text.strip(),
            data["file_id"],
            data["file_type"]
        ))

        await conn.commit()

    await state.clear()

    await message.answer(
        "✅ تمت إضافة المحتوى بنجاح.",
        reply_markup=admin_menu()
    )


# =========================================================
# DELETE CONTENT
# =========================================================

@dp.callback_query(F.data == "admin_delete_content")
async def delete_content_start(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user.id):
        await callback.answer("مش مسموح.", show_alert=True)
        return

    async with await db() as conn:

        cursor = await conn.execute("""
            SELECT id, display_name
            FROM contents
            ORDER BY id DESC
        """)

        rows = await cursor.fetchall()

    if not rows:

        await callback.message.edit_text(
            "🗑️ ما فيش محتوى للحذف.",
            reply_markup=back_button()
        )

        await callback.answer()
        return

    buttons = []

    for content_id, name in rows:

        buttons.append([
            InlineKeyboardButton(
                text=f"🗑️ {name}",
                callback_data=f"delete:{content_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔙 الإدارة",
            callback_data="admin"
        )
    ])

    await callback.message.edit_text(
        "🗑️ اختار المحتوى اللي تبي تحذفه:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        )
    )

    await callback.answer()


@dp.callback_query(F.data.startswith("delete:"))
async def delete_content(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer("مش مسموح.", show_alert=True)
        return

    content_id = int(
        callback.data.split(":")[1]
    )

    async with await db() as conn:

        await conn.execute("""
            DELETE FROM contents
            WHERE id = ?
        """, (content_id,))

        await conn.commit()

    await callback.answer(
        "تم حذف المحتوى."
    )

    await callback.message.edit_text(
        "✅ تم حذف المحتوى بنجاح.",
        reply_markup=admin_menu()
    )


# =========================================================
# UPDATE TREE
# =========================================================

@dp.callback_query(F.data == "admin_tree")
async def admin_tree(
    callback: CallbackQuery
):

    if not is_admin(callback.from_user.id):
        await callback.answer("مش مسموح.", show_alert=True)
        return

    await callback.message.answer(
        "🌳 ابعث ملف شجرة المواد هنا.\n\n"
        "تقدر ترفع الملف أو تعمل Forward لملف موجود عندك."
    )

    await callback.answer()


@dp.message(
    F.document
)
async def receive_tree_or_ignore(message: Message):

    if not is_admin(message.from_user.id):
        return

    # Don't treat documents as tree if admin is currently
    # adding content. FSM handlers have priority.

    state = await dp.fsm.get_context(
        bot=bot,
        chat_id=message.chat.id,
        user_id=message.from_user.id
    )

    current_state = await state.get_state()

    if current_state:
        return

    file_id = message.document.file_id

    async with await db() as conn:

        await conn.execute("""
            INSERT INTO settings(key, value)
            VALUES('tree_file', ?)
            ON CONFLICT(key)
            DO UPDATE SET value = excluded.value
        """, (file_id,))

        await conn.commit()

    await message.answer(
        "✅ تم تحديث شجرة المواد."
    )


# =========================================================
# RUN
# =========================================================

async def main():

    await init_db()

    print("CS Student Bot is running...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
