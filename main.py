import asyncio
import logging
import os
import sys
from deep_translator import GoogleTranslator
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
import sqlite3
from aiogram import F

TOKEN = os.environ['TOKEN']

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()
db_file = "word_database.db"

# Create and connect to the database
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Create the 'words' table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS words (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        word TEXT
    )
''')
conn.commit()

kb = ["remove all words", "show my list"]


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`

    kb = [
        [
            types.KeyboardButton(text="Remove all words"),
            types.KeyboardButton(text="Show my list")
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Select: "
    )
    await message.answer(f"Hello, {message.from_user.first_name}!", reply_markup=keyboard)


@dp.message(lambda f: f.text.lower() not in kb)
async def echo_handler(message: types.Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    user_id = message.from_user.id
    user_word = message.text
    print(user_word)
    translator = GoogleTranslator(source='en', target='uk')
    translated_word = translator.translate(user_word)

    # Check if the word is already in the database
    cursor.execute("SELECT * FROM words WHERE user_id=? AND word=?", (user_id, user_word))
    existing_word = cursor.fetchone()

    if existing_word:
        await message.reply(f"Word: {user_word}\nTranslation: {translated_word}")
    else:
        cursor.execute("INSERT INTO words (user_id, word) VALUES (?, ?)", (user_id, user_word))
        conn.commit()
        await message.reply(
            f"Word: {user_word}\nTranslation: {translated_word}")


@dp.message(F.text.lower() == 'show my list')
async def list_words(message: types.Message):
    user_id = message.from_user.id

    # Retrieve the user's words and translations from the database
    cursor.execute("SELECT word FROM words WHERE user_id=?", (user_id,))
    word_records = cursor.fetchall()

    if not word_records:
        await message.reply("Your word list is empty.")
    else:
        words_with_translations = []
        translator = GoogleTranslator(target='uk')

        for word_record in word_records:
            word = word_record[0]
            translation = translator.translate(word)
            words_with_translations.append(f"{word} - {translation}")

        word_list_text = "\n".join(words_with_translations)
        await message.reply(f"Your word list with translations:\n{word_list_text}")


# Function to handle the /cleanallwords command
@dp.message(F.text == 'Remove all words')
async def clean_all_words(message: types.Message):
    user_id = message.from_user.id

    # Check if the user has any words in their list
    cursor.execute("SELECT * FROM words WHERE user_id=?", (user_id,))
    existing_words = cursor.fetchall()

    if existing_words:
        # Remove all words from the user's list
        cursor.execute("DELETE FROM words WHERE user_id=?", (user_id,))
        conn.commit()
        await message.reply("All words have been removed from your list.")
    else:
        await message.reply("Your word list is already empty.")


async def send_daily_message(bot):
    while True:
        print('Hello')
        cursor.execute("SELECT DISTINCT user_id FROM words")
        user_ids = [row[0] for row in cursor.fetchall()]

        for user_id in user_ids:
            cursor.execute("SELECT word FROM words WHERE user_id=?", (user_id,))
            words = [row[0] for row in cursor.fetchall()]

            if words:
                # Select a random word from the user's list (you can change this logic)
                import random
                random_word = random.choice(words)
                translator = GoogleTranslator(target='uk')
                translation = translator.translate(random_word)

                # Send the daily message
                await bot.send_message(chat_id=user_id,
                                 text=f"Word of the Day: {random_word}\nTranslation: {translation}")
        await asyncio.sleep(3600)


async def main() -> None:
    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(TOKEN)
    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    bot = Bot(TOKEN)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(
        main(),
        send_daily_message(bot)
    ))