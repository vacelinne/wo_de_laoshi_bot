import asyncio
import json
import random
import string

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from aiohttp import web
import asyncio

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

with open('words.json', 'r', encoding='utf-8') as f:
       WORDS = json.load(f)

user_active_word = {}
user_progress = {}

def get_current_days():
       start_date = datetime(2026, 1, 1)
       today = datetime.now()
       return (today - start_date).days

def get_words_to_review(user_id, all_words, learned_words):
    today_days = get_current_days()
    progress = user_progress.get(user_id, {})
    words_to_review = []
    intervals = [0, 1, 3, 7, 14, 30]
    
    for hanzi in learned_words:
        if hanzi in progress:
            level = progress[hanzi]['level']
            last_review = progress[hanzi]['last_review']
            days_since_review = today_days - last_review
            if days_since_review >= intervals[level]:
                words_to_review.append(hanzi)
        else:
            words_to_review.append(hanzi)
    
    if not words_to_review:
        new_words = [w for w in all_words if w not in learned_words]
        return new_words
    else:
        return words_to_review

def get_main_keyboard():
       button = KeyboardButton(text="Новое слово")
       return ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)

def normalize(text):
       text = text.strip().lower()
       text = text.rstrip(string.punctuation)
       return text

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    button = KeyboardButton(text="Новое слово")
    keyboard = ReplyKeyboardMarkup (keyboard=[[button]], resize_keyboard=True)
    await message.answer("Бу! Испугался? Не бойся, это я, твой лаоши. \n\n"
                         "Подойди, нажми кнопку 'Новое слово', чтобы получить случайный иероглиф для первода.\n"
                         "Попробуй написать его перевод по-русски или пиньинь.",
                         reply_markup=get_main_keyboard()
                         )

async def send_new_word (message: types.Message):
      user_id = message.from_user.id
      all_words = list(WORDS.keys())
      learned_words = [hanzi for hanzi in all_words if user_id in user_progress and hanzi in user_progress.get(user_id, {})]
      words_to_review = get_words_to_review(user_id, all_words,learned_words)
      if not words_to_review:
            await message.answer(
                  "🎉 Поздравляю! Ты выучил все слова! Используй /reset, чтобы начать заново.",
                  reply_markup=get_main_keyboard()
            )
            return
      
      hanzi = random.choice(words_to_review)
      user_active_word[user_id] = hanzi
      await message.answer(f"Переведи слово:**{hanzi}**",
                            parse_mode="Markdown",
                            reply_markup=get_main_keyboard()
                            )

@dp.message(Command("word"))
async def cmd_word(message: types.Message):
       await send_new_word(message)

@dp.message(lambda message: message.text == "Новое слово")
async def button_word(message: types.Message):
       await send_new_word(message)

@dp.message(Command("reset"))
async def reset_progress(message: types.Message):
      user_id = message.from_user.id
      if user_id in user_progress:
            user_progress[user_id] = {}
      else:
            user_progress[user_id] = {}

            if user_id in user_active_word:
                  del user_active_word[user_id]

            await message.answer(
                  "Прогресс сброшен! Все слова снова доступны для изучения.",
                  reply_markup=get_main_keyboard()
            )

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
      user_id = message.from_user.id
      all_words = list(WORDS.keys())
      total_words = len(all_words)

      user_data = user_progress.get(user_id, {})
      learned_words = len(user_data)

      level_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
      for word_data in user_data.values():
            level = word_data.get('level', 0)
            level_counts[level] = level_counts.get(level, 0) + 1

      stats_text = (
             f"📊 **Твой прогресс:**\n\n"
             f"📚 Всего слов: **{total_words}**\n"
             f"✅ Выучено (хотя бы раз): **{learned_words}**\n"
             f"📈 Осталось: **{total_words - learned_words}**\n\n"
             f"**Уровни сложности:**\n"
             f"🆕 Новые (0): {level_counts.get(0, 0)}\n"
             f"🌟 Знаю (1): {level_counts.get(1, 0)}\n"
             f"🌟 Знаю (2): {level_counts.get(2, 0)}\n"
             f"🌟 Знаю (3): {level_counts.get(3, 0)}\n"
             f"🔥 Хорошо (4): {level_counts.get(4, 0)}\n"
             f"💪 Отлично (5): {level_counts.get(5, 0)}\n\n"
             f"_Чем выше уровень, тем реже слово будет появляться._"
       )
      await message.answer(stats_text, parse_mode="Markdown", reply_markup=get_main_keyboard())

@dp.message()
async def check_answer(message: types.Message):
       user_id = message.from_user.id

       if user_id in user_active_word:
              hanzi = user_active_word[user_id]
              correct_data = WORDS[hanzi]
              correct_pinyin = correct_data['pinyin'].lower()
              correct_translation_raw = correct_data['translation']

              possible_translations = [normalize(part) for part in correct_translation_raw.split(',')]

              user_answer = normalize(message.text)

              hint_keywords = ['не знаю', 'забыл', 'забыла', 'хз', 'подскажи', 'подсказка' 'пиньинь', 'помоги', 'не помню']
              if any(keyword in user_answer for keyword in hint_keywords):
                     await message.answer(
                            f"📖 Подсказка для иероглифа **{hanzi}**:\n"
                            f"Пиньинь: `{correct_pinyin}`\n\n"
                            f"Попробуй написать перевод.",
                            parse_mode="Markdown",
                            reply_markup=get_main_keyboard()
                     )
                     return

              if user_answer == correct_pinyin or user_answer in possible_translations:
                     today_days = get_current_days()
                     if user_id not in user_progress:
                           user_progress[user_id] = {}

                     current_level = user_progress[user_id].get(hanzi, {}).get('level', 0)
                     new_level = min(current_level + 1, 5)

                     user_progress[user_id][hanzi] = {
                           'level': new_level,
                           'last_review': today_days
                     }

                     await message.answer(
                            f"✅Правильно!\n"
                            f"Иероглиф: {hanzi}\n"
                            f"Пиньинь: {correct_pinyin}\n"
                            f"Перевод: {correct_translation_raw}\n\n"
                            f"Напиши /word, чтобы получить следующее слово.",
                            reply_markup=get_main_keyboard()
                     )

                     del user_active_word[user_id]
              else:
                     await message.answer(
                            f"❌Неправильно.\n"
                            f"Правильный пиньинь: {correct_pinyin}\n"
                            f"Правильный перевод: {correct_translation_raw}\n\n"
                            f"Попробуй ещё раз или возьми новое слово.",
                            reply_markup=get_main_keyboard()
                     )
       else:
              await message.answer(
                     "Сначала возьми слово для перевода с помощью команды /word или кнопки.",
                     reply_markup=get_main_keyboard()
              )

async def healthcheck(request):
      return web.Response(text="OK")

async def main():
        app = web.Application()
        app.router.add_get('/healthcheck', healthcheck)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 10000)
        await site.start()

        print("бот запущен и ждет команд...")
        await dp.start_polling(bot)

if __name__ == '__main__':
        asyncio.run(main())