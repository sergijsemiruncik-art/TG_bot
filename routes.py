from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from Forms.users import Form
from aiogram.fsm.context import FSMContext
import aiosqlite
from pathlib import Path
from os import getenv
from dotenv import load_dotenv

router = Router()

# Завантажуємо змінні середовища з .env файлу
load_dotenv()

PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "users.db"

# Завантажуємо ID адміністратора з .env файлу
ADMIN_ID = int(getenv('ADMIN_ID', 0))

async def init_db():
    """Ініціалізація бази даних"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                email TEXT NOT NULL
            )
        ''')
        await db.commit()

async def add_user(telegram_id: int, name: str, age: int, email: str):
    """Додавання користувача в базу даних"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'INSERT INTO users (telegram_id, name, age, email) VALUES (?, ?, ?, ?)',
            (telegram_id, name, age, email)
        )
        await db.commit()

async def get_all_users():
    """Отримання всіх користувачів з бази даних"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT name, age, email FROM users')
        users = await cursor.fetchall()
        return users

@router.message(Command('start'))
async def start(message: Message, state: FSMContext):
    await state.update_data(telegram_id=message.from_user.id)
    await message.answer("Введіть ваше імʼя")
    await state.set_state(Form.name)

@router.message(Command('cancel'))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Введення даних скасовано. Для повторного введення /start")

@router.message(Form.name, F.text)
async def proccess_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)

    await message.answer("Добре, а тепер введіть Ваш вік")
    await state.set_state(Form.age)


@router.message(Form.age, F.text)
async def proccess_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Вік повинен бути числом, спробуйте ще раз")
        return

    if int(message.text) < 1 or int(message.text) > 100:
        await message.answer("Вік повинен бути в діапазоні від 1 до 100, спробуйте ще раз")
        return

    await state.update_data(age=int(message.text))

    await message.answer("Добре, Ваш вік збережено !\n Тепер введіть Ваш email")
    await state.set_state(Form.email)


@router.message(Form.email, F.text)
async def proccess_email(message: Message, state: FSMContext):
    if '@' not in message.text or '.' not in message.text:
        await message.answer("Невірний формат email, спробуйте еще раз")
        return

    await state.update_data(email=message.text)

    data = await state.get_data()
    telegram_id = data.get('telegram_id')
    name = data.get('name')
    age = data.get('age')
    email = data.get('email')

    try:
        await add_user(telegram_id, name, age, email)
        await message.answer(f"✅ Ваші дані збережено у базі даних!\n"
                             f"Ім'я: {name}\n"
                             f"Вік: {age}\n"
                             f"Email: {email}\n"
                             f"ID Telegram: {telegram_id}")
    except Exception as e:
        await message.answer(f"❌ Помилка при збереженні даних: {str(e)}")
    
    await state.clear()

@router.message(Command('users'))
async def show_users(message: Message):
    # Перевірка прав адміністратора
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Такої команди не існує !")
        return
    
    try:
        await init_db()
        users = await get_all_users()
        
        if not users:
            await message.answer("📭 Поки що немає зареєстрованих користувачів.")
            return
        
        text = "📋 Зареєстровані користувачі:\n\n"
        for i, (name, age, email) in enumerate(users, 1):
            text += f"{i}. Ім'я: {name}\n   Вік: {age}\n   Email: {email}\n\n"
        
        await message.answer(text)
    except Exception as e:
        await message.answer(f"❌ Помилка при отриманні даних: {str(e)}")
