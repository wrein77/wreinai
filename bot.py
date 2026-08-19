import os
import asyncio

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from groq import Groq


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.getenv("8747215142:AAHQvxuno7sLoGJQr0-ryX82vUSKJDHOuZs")
GROQ_API_KEY = os.getenv("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")

MODEL = "openai/gpt-oss-120b"

if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN")

if not GROQ_API_KEY:
    raise RuntimeError("Не задан GROQ_API_KEY")


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

groq = Groq(api_key=GROQ_API_KEY)


# =========================
# ПАМЯТЬ
# =========================

# user_id -> история сообщений
memory = {}

MAX_MESSAGES = 12


SYSTEM_PROMPT = """
Ты — WREIN AI, умный и дружелюбный ИИ-ассистент в Telegram.

Отвечай понятно, естественно и без лишней воды.
Если пользователь пишет по-русски — отвечай по-русски.
Если пишет на другом языке — отвечай на этом языке.

Ты умеешь:
- объяснять сложные темы простыми словами;
- помогать с программированием;
- помогать с учёбой;
- придумывать идеи;
- отвечать на обычные вопросы;
- поддерживать нормальный диалог.

Не выдумывай факты, если не уверен.
"""


# =========================
# КЛАВИАТУРА
# =========================

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


# =========================
# START
# =========================

@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "🤖 <b>WREIN AI</b>\n\n"
        "Привет! Я твой ИИ-ассистент.\n\n"
        "Просто отправь мне сообщение — и я отвечу.\n\n"
        "🧠 Я запоминаю контекст разговора.",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )


# =========================
# CLEAR
# =========================

@dp.message(Command("clear"))
async def clear_command(message: Message):

    memory.pop(message.from_user.id, None)

    await message.answer(
        "🧹 Память очищена.\n\n"
        "Можем начать новый разговор."
    )


@dp.callback_query(F.data == "clear")
async def clear_callback(callback: CallbackQuery):

    memory.pop(callback.from_user.id, None)

    await callback.message.answer(
        "🧹 <b>Новый чат создан.</b>\n\n"
        "Старый контекст очищен.",
        parse_mode="HTML"
    )

    await callback.answer("Готово!")


# =========================
# HELP
# =========================

@dp.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):

    await callback.message.answer(
        "ℹ️ <b>Как пользоваться</b>\n\n"
        "Просто напиши мне сообщение.\n\n"
        "Например:\n"
        "• Объясни производную\n"
        "• Напиши Python-код\n"
        "• Придумай название проекта\n"
        "• Что такое нейросеть?\n"
        "• Помоги разобраться с ошибкой\n\n"
        "/clear — очистить память",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================
# AI
# =========================

async def ask_ai(user_id: int, text: str):

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

    def request():

        completion = groq.chat.completions.create(
            model=MODEL,
            messages=memory[user_id],
            temperature=0.7,
            max_completion_tokens=2048,
            top_p=1,
            stream=False
        )

        return completion.choices[0].message.content

    answer = await asyncio.to_thread(request)

    if not answer:
        answer = "Не получилось получить ответ."

    memory[user_id].append(
        {
            "role": "assistant",
            "content": answer
        }
    )

    return answer


# =========================
# СООБЩЕНИЯ
# =========================

@dp.message(F.text)
async def message_handler(message: Message):

    text = message.text.strip()

    if not text:
        return

    # Показываем пользователю, что бот думает
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action="typing"
    )

    try:

        answer = await ask_ai(
            message.from_user.id,
            text
        )

        # Telegram ограничивает длину одного сообщения
        if len(answer) <= 4096:

            await message.answer(
                answer,
                reply_markup=main_keyboard()
            )

        else:

            # Разбиваем длинный ответ
            for i in range(0, len(answer), 4096):

                await message.answer(
                    answer[i:i + 4096]
                )

    except Exception as e:

        print("ERROR:", e)

        await message.answer(
            "❌ Произошла ошибка при обращении к ИИ.\n\n"
            "Попробуй ещё раз через несколько секунд."
        )


# =========================
# ЗАПУСК
# =========================

async def main():

    print("🤖 WREIN AI запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
