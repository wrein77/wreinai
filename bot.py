import os
import asyncio
import base64

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from groq import Groq


# ==============================
# НАСТРОЙКИ
# ==============================

BOT_TOKEN = os.getenv("8747215142:AAHQvxuno7sLoGJQr0-ryX82vUSKJDHOuZs")
GROQ_API_KEY = os.getenv("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")

TEXT_MODEL = "openai/gpt-oss-120b"
VISION_MODEL = "qwen/qwen3.6-27b"

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN")

if not GROQ_API_KEY:
    raise RuntimeError("Не задан GROQ_API_KEY")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

groq = Groq(api_key=GROQ_API_KEY)


# ==============================
# ПАМЯТЬ
# ==============================

memory = {}

MAX_MESSAGES = 12


SYSTEM_PROMPT = """
Ты — WREIN AI, персональный ИИ-ассистент в Telegram.

Отвечай естественно, понятно и без лишней воды.

Если пользователь пишет на русском — отвечай на русском.

Ты умеешь:
- отвечать на вопросы;
- объяснять сложные темы;
- помогать с программированием;
- помогать с учёбой;
- анализировать фотографии;
- распознавать текст на фотографиях;
- объяснять изображения.

Не утверждай, что умеешь работать с файлами,
PDF или другими функциями, которых у тебя нет.

Будь дружелюбным и полезным.
"""


# ==============================
# КНОПКИ
# ==============================

def main_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧠 Новый чат",
                    callback_data="clear"
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="help"
                )
            ]
        ]
    )


# ==============================
# START
# ==============================

@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "🤖 <b>WREIN AI</b>\n\n"
        "Привет! Я твой ИИ-ассистент.\n\n"
        "📝 Напиши мне вопрос\n"
        "🖼 Отправь фотографию\n\n"
        "Я постараюсь помочь.",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


# ==============================
# ПОМОЩЬ
# ==============================

@dp.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):

    await callback.message.answer(
        "ℹ️ <b>Что я умею</b>\n\n"
        "🧠 ИИ-чат\n"
        "🖼 Анализ фотографий\n"
        "🔤 Распознавание текста на фото\n"
        "📚 Помощь с учёбой\n"
        "💻 Помощь с программированием\n"
        "💡 Генерация идей\n\n"
        "/clear — очистить память",
        parse_mode="HTML"
    )

    await callback.answer()


# ==============================
# НОВЫЙ ЧАТ
# ==============================

@dp.message(Command("clear"))
async def clear_command(message: Message):

    memory.pop(
        message.from_user.id,
        None
    )

    await message.answer(
        "🧹 Память очищена.\n\n"
        "Можем начать новый разговор."
    )


@dp.callback_query(F.data == "clear")
async def clear_callback(callback: CallbackQuery):

    memory.pop(
        callback.from_user.id,
        None
    )

    await callback.message.answer(
        "🧹 <b>Новый чат создан!</b>\n\n"
        "Контекст предыдущего разговора очищен.",
        parse_mode="HTML"
    )

    await callback.answer("Готово")


# ==============================
# GROQ — ТЕКСТ
# ==============================

def request_text(messages):

    response = groq.chat.completions.create(
        model=TEXT_MODEL,
        messages=messages,
        temperature=0.7,
        max_completion_tokens=2048,
        stream=False
    )

    return response.choices[0].message.content


async def ask_ai(user_id, text):

    if user_id not in memory:

        memory[user_id] = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

    memory[user_id].append(
        {
            "role": "user",
            "content": text
        }
    )

    # Оставляем system prompt + последние сообщения
    memory[user_id] = (
        [memory[user_id][0]]
        + memory[user_id][-MAX_MESSAGES:]
    )

    answer = await asyncio.to_thread(
        request_text,
        memory[user_id]
    )

    memory[user_id].append(
        {
            "role": "assistant",
            "content": answer
        }
    )

    return answer


# ==============================
# ОБЫЧНЫЙ ТЕКСТ
# ==============================

@dp.message(F.text)
async def text_handler(message: Message):

    if message.text.startswith("/"):
        return

    await bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )

    try:

        answer = await ask_ai(
            message.from_user.id,
            message.text
        )

        await send_long_message(
            message,
            answer
        )

    except Exception as e:

        print("TEXT ERROR:", e)

        await message.answer(
            "❌ Произошла ошибка при обращении к ИИ."
        )


# ==============================
# ФОТО
# ==============================

@dp.message(F.photo)
async def photo_handler(message: Message):

    await bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )

    path = None

    try:

        # Берём самое качественное фото
        photo = message.photo[-1]

        telegram_file = await bot.get_file(
            photo.file_id
        )

        # Временный файл
        with open(
            "temp_image.jpg",
            "wb"
        ) as image:

            await bot.download_file(
                telegram_file.file_path,
                image
            )

        path = "temp_image.jpg"

        # Кодируем изображение
        with open(
            path,
            "rb"
        ) as image:

            image_base64 = base64.b64encode(
                image.read()
            ).decode("utf-8")

        # Если пользователь написал подпись к фото
        question = message.caption

        if not question:

            question = (
                "Проанализируй это изображение. "
                "Опиши, что на нём изображено. "
                "Если есть текст, распознай его."
            )

        response = await asyncio.to_thread(
            lambda: groq.chat.completions.create(
                model=VISION_MODEL,

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": question
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url":
                                        "data:image/jpeg;base64,"
                                        + image_base64
                                }
                            }
                        ]
                    }
                ],

                temperature=0.4,
                max_completion_tokens=2048,
                stream=False
            )
        )

        answer = response.choices[0].message.content

        await send_long_message(
            message,
            answer
        )

    except Exception as e:

        print("IMAGE ERROR:", e)

        await message.answer(
            "❌ Не получилось обработать фотографию.\n\n"
            "Попробуй отправить её ещё раз."
        )

    finally:

        if path and os.path.exists(path):

            os.remove(path)


# ==============================
# ДЛИННЫЕ ОТВЕТЫ
# ==============================

async def send_long_message(
    message,
    text
):

    if not text:

        text = "Не удалось получить ответ."

    # Telegram ограничивает длину сообщения
    for i in range(
        0,
        len(text),
        4000
    ):

        await message.answer(
            text[i:i + 4000]
        )


# ==============================
# ЗАПУСК
# ==============================

async def main():

    print("🤖 WREIN AI запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
