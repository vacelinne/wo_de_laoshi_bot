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

def normalize_russian(text):
      text = normalize(text)
      text = text.replace ('ё', 'е')
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
      user_data = user_progress.get(user_id, {})

      if not user_data:
            await message.answer(
                  "У тебя пока нет статистики. Начни учить слова с /word!",
                  reply_markup=get_main_keyboard()
            )
            return
      
      total_correct = sum(data.get('correct', 0) for data in user_data.values())
      total_wrong = sum(data.get('wrong', 0) for data in user_data.values())
      total_missed = sum(data.get('missed', 0) for data in user_data.values())
      total_attempts = total_correct + total_wrong

      accuracy = round((total_correct / total_attempts) * 100, 1) if total_attempts > 0 else 0

      stats_text = (
             f"📊 **Твой прогресс:**\n\n"
             f"✅ Правильно: **{total_correct}**\n"
             f"❌ Неправильно: **{total_wrong}**\n"
             f"⏩ Пропущено: **{total_missed}**\n"
             f"🎯 Точность: **{accuracy}%**\n\n"
             f"📚 Слов в изучении: **{len(user_data)}**\n\n"
             f"_Статистика с начала работы с ботом (без учёта перезапусков)._"
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

              possible_translations = [normalize_russian(part) for part in correct_translation_raw.split(',')]

              user_answer = normalize_russian(message.text)

              hint_keywords = ['не знаю', 'забыл', 'забыла', 'хз', 'подскажи', 'подсказка', 'пиньинь', 'помоги', 'не помню']
              if any(keyword in user_answer for keyword in hint_keywords):
                     if user_id in user_progress and hanzi in user_progress[user_id]:
                           user_progress[user_id][hanzi]['missed'] += 1
                     await message.answer(
                            f"📖 Подсказка для иероглифа **{hanzi}**:\n"
                            f"Пиньинь: `{correct_pinyin}`\n\n"
                            f"Попробуй написать перевод.",
                            parse_mode="Markdown",
                            reply_markup=get_main_keyboard()
                     )
                     return
              is_correct = False

              if user_answer == correct_pinyin or user_answer in possible_translations:
                     is_correct = True
              elif any(word in correct_translation_raw for word in user_answer.split()):
                     is_correct = True
              if is_correct:
                     today_days = get_current_days()
                     if user_id not in user_progress:
                           user_progress[user_id] = {}

                     if hanzi not in user_progress[user_id]:
                           user_progress[user_id][hanzi] = {
                                 'level': 0,
                                 'last_review': 0,
                                 'correct' : 0,
                                 'wrong': 0,
                                 'missed': 0
                           }
                     
                     user_progress[user_id][hanzi]['correct'] += 1
              

                     current_level = user_progress[user_id][hanzi].get('level', 0)
                     new_level = min(current_level + 1, 5)

                     user_progress[user_id][hanzi]['level'] = new_level
                     user_progress[user_id][hanzi]['last_review'] = today_days

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
                     if user_id in user_progress:
                           user_progress[user_id] = {}

                     if hanzi in user_progress[user_id]:
                            user_progress[user_id][hanzi]['wrong'] += 1
                     else:
                            user_progress[user_id][hanzi] = {
                                   'level': 0,
                                   'last_review': 0,
                                   'correct': 0,
                                   'wrong': 1,
                                   'missed': 0
                                   }

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