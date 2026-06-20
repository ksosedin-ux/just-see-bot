import os
import json
import logging
import asyncio
from datetime import datetime, time, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
DATA_FILE = "data.json"

PLAN = [
    {"d": "День 1", "theme": "КП-финал", "tasks": [
        "Дожать черновик КП до финала: заполнить слайд Нового Херсонеса, проверить все цифры",
        "Написать 3-строчный питч: кто мы, что делаем, почему нам доверяют",
        "Сохранить КП в PDF — готово к отправке"]},
    {"d": "День 2", "theme": "Соцсети-база", "tasks": [
        "Оформить шапку Instagram + VK: описание, ссылка, highlights-папки",
        "Опубликовать вводный пост: кто такие Just See, почему MAUR набрал 4.6М",
        "Запланировать 6 постов на 2 недели в любом планировщике"]},
    {"d": "День 3", "theme": "База лидов", "tasks": [
        "Составить список 30 артистов / лейблов Москвы — у кого нет клипа или старый",
        "Найти Instagram/TG каждого — зафиксировать в Google-таблице",
        "Написать шаблон первого DM для артиста (2–3 строки, без шаблонщины)"]},
    {"d": "День 4", "theme": "Первые касания — артисты", "tasks": [
        "Отправить 10 DM артистам по шаблону из дня 3",
        "Опубликовать BTS-пост со съёмки (любой, даже старый материал)",
        "Зафиксировать все отправленные в CRM-таблице: имя, канал, дата, статус"]},
    {"d": "День 5", "theme": "Агентства", "tasks": [
        "Составить список 20 рекламных агентств Москвы (VK Ads, AdIndex, Telegram)",
        "Найти ЛПР каждого — продюсер, арт-директор, аккаунт",
        "Написать шаблон письма для агентства (субподряд-позиционирование)"]},
    {"d": "День 6", "theme": "Первые касания — агентства", "tasks": [
        "Отправить 10 писем агентствам",
        "Опубликовать Reels-тизер Cemetery of Ideas эпизод 1",
        "Ретро дня: кто ответил, кто открыл — обновить CRM"]},
    {"d": "День 7", "theme": "Ретро недели 1", "tasks": [
        "Посчитать: сколько отправлено, сколько ответов, сколько отказов",
        "Написать 2-й follow-up тем, кто не ответил (одно предложение)",
        "Скорректировать шаблоны — что зашло, что нет"]},
    {"d": "День 8", "theme": "Контент + лиды", "tasks": [
        "Выпустить Cemetery of Ideas эпизод 1 (полный)",
        "Отправить 15 новых DM артистам",
        "Добавить 20 новых агентств в базу"]},
    {"d": "День 9", "theme": "Тёплые касания", "tasks": [
        "Написать 3 старым клиентам — как дела + намекнуть на новые форматы",
        "Опубликовать кейс-пост: MAUR — цифры, процесс, результат",
        "Отправить 10 писем новым агентствам"]},
    {"d": "День 10", "theme": "Лид-магнит", "tasks": [
        "Сделать PDF '3 ошибки артистов при съёмке клипа' — 1 страница",
        "Разослать лид-магнит всем, кто ответил но не купил",
        "Опубликовать пост-мнение: почему дешёвый клип убивает образ артиста"]},
    {"d": "День 11", "theme": "Первый созвон", "tasks": [
        "Довести до звонка хотя бы 1 заинтересованного — назначить встречу",
        "Отправить 15 новых DM/писем (микс артисты + агентства)",
        "Обновить CRM — все статусы актуальны"]},
    {"d": "День 12", "theme": "Контент", "tasks": [
        "Выпустить Cemetery of Ideas эпизод 2",
        "Опубликовать BTS-видео или фото со съёмки",
        "Ответить на все комментарии и DM — не игнорировать"]},
    {"d": "День 13", "theme": "Встреча", "tasks": [
        "Провести 1–2 звонка/встречи с заинтересованными",
        "После каждой встречи — отправить КП в течение 2 часов",
        "Зафиксировать следующий шаг по каждому лиду"]},
    {"d": "День 14", "theme": "Ретро фазы 1", "tasks": [
        "Итог: лидов в базе / звонков / КП отправлено / ответов",
        "Определить: какой канал дал больше всего ответов — удвоить",
        "Составить конкретный план фазы 2 с правками под реальность"]},
    {"d": "Дни 15–16", "theme": "Разгон охвата", "tasks": [
        "Отправить 30 новых контактов за 2 дня (15 в день)",
        "Провести 2 звонка с тёплыми из фазы 1",
        "Выпустить Cemetery of Ideas эпизод 3"]},
    {"d": "Дни 17–18", "theme": "Дожим", "tasks": [
        "Follow-up всем, кто получил КП но не ответил — звонок или голосовое",
        "Опубликовать кейс РФА: что сняли, зачем, результат",
        "Добавить 30 новых контактов в базу"]},
    {"d": "Дни 19–21", "theme": "Встречи", "tasks": [
        "Провести 3–4 встречи / звонка за 3 дня",
        "После каждой — конкретный следующий шаг",
        "Опубликовать 2 поста: BTS + мнение о рынке"]},
    {"d": "Дни 22–24", "theme": "Контент-волна", "tasks": [
        "Выпустить эпизоды 4 и 5 Cemetery of Ideas",
        "Опубликовать отзыв от любого клиента",
        "Запустить таргет VK: бюджет 3–5 тыс. руб., ведёт на профиль"]},
    {"d": "Дни 25–28", "theme": "Закрытие первого", "tasks": [
        "Цель — подписать 1 договор. Предложи мини-формат или пилот",
        "Собрать 3 отзыва от прошлых клиентов — оформить в пост",
        "Расширить базу до 100+ контактов"]},
    {"d": "Дни 29–31", "theme": "Новая волна", "tasks": [
        "Отправить 40 новых холодных (малый бизнес, кафе, бренды одежды)",
        "Выпустить Cemetery of Ideas эпизоды 6–7",
        "Провести 4–5 звонков за 3 дня"]},
    {"d": "Дни 32–35", "theme": "Ретро фазы 2", "tasks": [
        "Итог: договоров / встреч / лидов / лучший канал",
        "Скорректировать оффер — что чаще всего отталкивало клиентов",
        "Записать Reels с итогами первого месяца продакшена"]},
    {"d": "Дни 36–38", "theme": "Работа с тёплыми", "tasks": [
        "Перейти только на тёплых — холодную рассылку делегировать",
        "Провести 3 встречи с наиболее горячими лидами",
        "Выпустить эпизоды 8–9 Cemetery of Ideas"]},
    {"d": "Дни 39–42", "theme": "Второй договор", "tasks": [
        "Закрыть 2-й договор",
        "Запустить производство — фиксировать процесс для контента",
        "Запустить реферальную программу: попроси каждого клиента назвать 1–2 контакта"]},
    {"d": "Дни 43–46", "theme": "Новая ниша", "tasks": [
        "Отправить 30 писем в новую нишу (event-агентства, музыкальные школы)",
        "Опубликовать 3 поста: кейс + BTS + мнение",
        "Сделать апселл действующему клиенту — доп. формат или ролик"]},
    {"d": "Дни 47–50", "theme": "Третий договор", "tasks": [
        "Закрыть 3-й договор",
        "Выпустить финальные эпизоды Cemetery of Ideas + анонс сезона 2",
        "Обновить КП с новыми кейсами и цифрами"]},
    {"d": "Дни 51–55", "theme": "Анализ и система", "tasks": [
        "Что работало лучше всего — канал, тип клиента, оффер? Зафиксировать",
        "Написать скрипт для Жени или фрилансера на типовые продажи",
        "Опубликовать Reels с итогами 2 месяцев"]},
    {"d": "Дни 56–60", "theme": "Планирование месяц 3", "tasks": [
        "Финальный ретро: выручка, лиды, договоры, подписчики",
        "Поставить цели на следующие 60 дней с новыми данными",
        "Запустить следующий цикл — теперь с опытом и базой"]},
]

XP_PER_TASK = 100
STREAK_BONUS = 50

RANKS = [
    (0, "🎬 Новичок"),
    (500, "📹 Оператор"),
    (1500, "🎥 Режиссёр"),
    (3000, "⭐ Продюсер"),
    (6000, "🏆 Топ-продакшен"),
    (10000, "👑 Just See Legend"),
]

GOAL_AMOUNT = 1_000_000  # рублей
AVG_PROJECT = 80_000     # средний чек клипа

HOURLY_PINGS = [
    "Эй, босс 👋 Как дела? Что по задачам?",
    "Час прошёл ⏱ Заглянул проверить — всё идёт по плану?",
    "Just See не спит 👀 Задачи двигаются?",
    "Привет! Напоминаю — у тебя сегодня дела. Как успехи?",
    "Дружеский пинг 🏓 Что сделано за последний час?",
]

ALL_DONE_MESSAGES = [
    "🎉 НА СЕГОДНЯ ДЕЛ БОЛЬШЕ НЕТ!\n\nСпасибо за крутой день, босс 🤝\nJust See растёт именно так — день за днём.",
    "💥 ВСЁ ЗАКРЫТО!\n\nТы сделал всё что надо. Спасибо за крутой день, босс 👊\nЭто и есть путь к миллиону.",
    "🏆 ДЕНЬ ЗАКРЫТ ЧИСТО!\n\nНа сегодня всё, босс. Серьёзный человек — серьёзный результат 🔥",
]

MORNING_QUOTES = [
    "Продакшены не строятся пока ты спишь. Но план уже готов 💪",
    "Клиенты не придут сами. Зато 3 задачи сегодня приблизят тебя к этому.",
    "MAUR набрал 4.6М. Следующий рекорд начинается сегодня.",
    "Один час утром на продажи = одна неделя не в ноль.",
    "Сегодня ты строишь то, что через 2 месяца будет работать само.",
]

EVENING_FAIL = [
    "Не всё сделано — и это ок. Перенесём, не потеряем.",
    "Один день не решает. Решает система. Завтра берёшь реванш.",
    "Производство сожрало день? Бывает. Завтра — сначала продажи.",
]

EVENING_WIN = [
    "🔥 Все три! Ты серьёзный человек.",
    "💎 Закрыл день чисто. Just See растёт.",
    "⚡ Именно так строятся продакшены. День за днём.",
]


def load_data():
    if Path(DATA_FILE).exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {
        "current_day": 0,
        "tasks_done": {},
        "xp": 0,
        "streak": 0,
        "last_active": None,
        "total_tasks_done": 0,
        "total_tasks": 0,
        "started": False,
        "extra_tasks": [],
    }


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_rank(xp):
    rank = RANKS[0][1]
    for threshold, name in RANKS:
        if xp >= threshold:
            rank = name
    return rank


def get_next_rank(xp):
    for threshold, name in RANKS:
        if xp < threshold:
            return threshold, name
    return None, None


def day_tasks_key(day_idx):
    return str(day_idx)


def get_today_tasks(data):
    day_idx = data["current_day"]
    if day_idx >= len(PLAN):
        return None
    day = PLAN[day_idx].copy()
    extra = data.get("extra_tasks", [])
    if extra:
        day["tasks"] = extra + day["tasks"]
    return day


def get_done_mask(data):
    key = day_tasks_key(data["current_day"])
    return data["tasks_done"].get(key, [])


def build_tasks_keyboard(data):
    day = get_today_tasks(data)
    if not day:
        return None
    done_mask = get_done_mask(data)
    keyboard = []
    all_tasks = day["tasks"]
    for i, task in enumerate(all_tasks):
        done = i < len(done_mask) and done_mask[i]
        emoji = "✅" if done else "⬜"
        short = task[:40] + "…" if len(task) > 40 else task
        keyboard.append([InlineKeyboardButton(f"{emoji} {short}", callback_data=f"task_{i}")])
    keyboard.append([InlineKeyboardButton("📊 Мой прогресс", callback_data="progress")])
    return InlineKeyboardMarkup(keyboard)


async def send_morning_briefing(app, chat_id):
    data = load_data()
    if not data["started"]:
        return
    day = get_today_tasks(data)
    if not day:
        return

    import random
    quote = random.choice(MORNING_QUOTES)
    day_num = data["current_day"] + 1
    rank = get_rank(data["xp"])
    streak = data["streak"]
    streak_line = f"🔥 Стрик: {streak} дней подряд" if streak > 0 else "Начни стрик сегодня!"

    extra = data.get("extra_tasks", [])
    extra_line = ""
    if extra:
        extra_line = f"\n\n⚠️ <b>Перенесено с вчера ({len(extra)} шт.):</b>\n" + "\n".join(f"• {t}" for t in extra)

    tasks_text = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(day["tasks"]))

    text = (
        f"☀️ <b>Доброе утро, Кирилл!</b>\n\n"
        f"<i>{quote}</i>\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📅 <b>{day['d']} — {day['theme']}</b>\n"
        f"Ранг: {rank} | XP: {data['xp']} | {streak_line}\n"
        f"━━━━━━━━━━━━━━━"
        f"{extra_line}\n\n"
        f"<b>Задачи на сегодня:</b>\n{tasks_text}\n\n"
        f"Отмечай по мере выполнения 👇"
    )

    await app.bot.send_message(
        chat_id=chat_id, text=text,
        parse_mode="HTML",
        reply_markup=build_tasks_keyboard(data)
    )


async def send_midday_check(app, chat_id):
    data = load_data()
    if not data["started"]:
        return
    done_mask = get_done_mask(data)
    done_count = sum(1 for d in done_mask if d)
    day = get_today_tasks(data)
    if not day:
        return
    total = len(day["tasks"])

    if done_count == 0:
        msg = "⚡ <b>Дневная проверка</b>\n\nЕщё ни одной задачи не закрыто. Один час сейчас = прогресс продакшена. Погнали?"
    elif done_count == total:
        msg = f"🏆 <b>Дневная проверка</b>\n\nВсе {total} задачи закрыты до обеда! Продуктивный день засчитан. Можешь взять доп. задачу или отдохнуть."
    else:
        left = total - done_count
        msg = f"💪 <b>Дневная проверка</b>\n\nСделано {done_count}/{total}. Осталось {left} — это {left * 20} минут максимум. Закроем до вечера?"

    await app.bot.send_message(
        chat_id=chat_id, text=msg,
        parse_mode="HTML",
        reply_markup=build_tasks_keyboard(data)
    )


async def send_evening_report(app, chat_id):
    data = load_data()
    if not data["started"]:
        return

    done_mask = get_done_mask(data)
    day = get_today_tasks(data)
    if not day:
        return

    all_tasks = day["tasks"]
    total = len(all_tasks)
    done_count = sum(1 for d in done_mask if d)
    failed_tasks = [all_tasks[i] for i in range(total) if i >= len(done_mask) or not done_mask[i]]

    import random

    xp_earned = 0
    if done_count > 0:
        xp_earned = done_count * XP_PER_TASK
        if done_count == total:
            data["streak"] = data.get("streak", 0) + 1
            xp_earned += data["streak"] * STREAK_BONUS
        else:
            data["streak"] = 0
        data["xp"] = data.get("xp", 0) + xp_earned
        data["total_tasks_done"] = data.get("total_tasks_done", 0) + done_count

    rank = get_rank(data["xp"])
    next_thresh, next_rank = get_next_rank(data["xp"])

    progress_bar = ""
    filled = int((done_count / total) * 10)
    progress_bar = "█" * filled + "░" * (10 - filled)

    if done_count == total:
        verdict = random.choice(EVENING_WIN)
    else:
        verdict = random.choice(EVENING_FAIL)

    next_rank_line = ""
    if next_thresh:
        gap = next_thresh - data["xp"]
        next_rank_line = f"\n🎯 До ранга <b>{next_rank}</b>: {gap} XP"

    failed_line = ""
    if failed_tasks:
        failed_line = "\n\n⏭ <b>Переносим на завтра:</b>\n" + "\n".join(f"• {t}" for t in failed_tasks)
        data["extra_tasks"] = failed_tasks
    else:
        data["extra_tasks"] = []

    text = (
        f"🌙 <b>Итог дня — {day['d']}</b>\n\n"
        f"{verdict}\n\n"
        f"[{progress_bar}] {done_count}/{total}\n"
        f"💰 XP за сегодня: +{xp_earned}\n"
        f"⚡ Всего XP: {data['xp']}\n"
        f"🏅 Ранг: {rank}\n"
        f"🔥 Стрик: {data['streak']} дней"
        f"{next_rank_line}"
        f"{failed_line}\n\n"
        f"Завтра — <b>{PLAN[min(data['current_day']+1, len(PLAN)-1)]['d']}: {PLAN[min(data['current_day']+1, len(PLAN)-1)]['theme']}</b>"
    )

    data["current_day"] = min(data["current_day"] + 1, len(PLAN) - 1)
    data["last_active"] = datetime.now().isoformat()
    save_data(data)

    await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    text = (
        "🎬 <b>Just See Production — Бот роста</b>\n\n"
        "Я слежу за твоим планом на 60 дней и не дам тебе съехать.\n\n"
        "Каждый день:\n"
        "• ☀️ 09:00 — утренний брифинг с задачами\n"
        "• ☀️ 13:00 — дневная проверка\n"
        "• 🌙 21:00 — итог дня + XP + перенос задач\n\n"
        "Команды:\n"
        "/go — начать план\n"
        "/tasks — задачи сегодня\n"
        "/progress — мой прогресс и ранг\n"
        "/stats — статистика за все дни\n"
        "/skip — пропустить день (использовать с умом)\n\n"
        "Готов?"
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Поехали!", callback_data="start_plan")]])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def go_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    data["started"] = True
    data["current_day"] = 0
    data["xp"] = 0
    data["streak"] = 0
    data["tasks_done"] = {}
    data["extra_tasks"] = []
    save_data(data)
    day = PLAN[0]
    text = (
        f"✅ <b>План запущен!</b>\n\n"
        f"Старт: <b>{day['d']} — {day['theme']}</b>\n\n"
        f"Задачи:\n" + "\n".join(f"  {i+1}. {t}" for i, t in enumerate(day["tasks"])) +
        "\n\nОтмечай по мере выполнения:"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=build_tasks_keyboard(data))


async def tasks_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["started"]:
        await update.message.reply_text("Сначала запусти план: /go")
        return
    day = get_today_tasks(data)
    if not day:
        await update.message.reply_text("🏆 Все 60 дней пройдены! Ты сделал это.")
        return
    done_mask = get_done_mask(data)
    done_count = sum(1 for d in done_mask if d)
    total = len(day["tasks"])
    text = (
        f"📋 <b>{day['d']} — {day['theme']}</b>\n"
        f"Выполнено: {done_count}/{total}\n\n"
        "Отмечай выполненные:"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=build_tasks_keyboard(data))


async def progress_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    xp = data.get("xp", 0)
    rank = get_rank(xp)
    next_thresh, next_rank = get_next_rank(xp)
    streak = data.get("streak", 0)
    day_num = data.get("current_day", 0) + 1
    total_done = data.get("total_tasks_done", 0)

    bar_filled = int((day_num / 60) * 20)
    day_bar = "█" * bar_filled + "░" * (20 - bar_filled)

    next_line = f"\n🎯 До <b>{next_rank}</b>: {next_thresh - xp} XP" if next_thresh else "\n👑 Максимальный ранг!"

    text = (
        f"📊 <b>Твой прогресс — Just See Production</b>\n\n"
        f"🏅 Ранг: <b>{rank}</b>\n"
        f"⚡ XP: <b>{xp}</b>"
        f"{next_line}\n"
        f"🔥 Стрик: <b>{streak}</b> дней подряд\n\n"
        f"📅 День: <b>{day_num}/60</b>\n"
        f"[{day_bar}]\n\n"
        f"✅ Задач выполнено: <b>{total_done}</b>\n"
        f"💎 Эффективность: <b>{round(total_done / max(day_num * 3, 1) * 100)}%</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def stats_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    lines = ["📈 <b>История дней</b>\n"]
    for i in range(data.get("current_day", 0)):
        key = str(i)
        mask = data["tasks_done"].get(key, [])
        done = sum(1 for d in mask if d)
        total = len(PLAN[i]["tasks"])
        bar = "█" * done + "░" * (total - done)
        lines.append(f"<b>{PLAN[i]['d']}</b> [{bar}] {done}/{total}")
    if len(lines) == 1:
        lines.append("Пока нет завершённых дней.")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def skip_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    day = get_today_tasks(data)
    if not day:
        return
    undone = [t for i, t in enumerate(day["tasks"])
              if i >= len(get_done_mask(data)) or not get_done_mask(data)[i]]
    data["extra_tasks"] = undone + data.get("extra_tasks", [])
    data["streak"] = 0
    data["current_day"] = min(data["current_day"] + 1, len(PLAN) - 1)
    save_data(data)
    await update.message.reply_text(
        f"⏭ День пропущен. {len(undone)} незакрытых задач перенесено на завтра.\nСтрик сброшен. Завтра берёшь реванш.",
        parse_mode="HTML"
    )


async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()

    if query.data == "start_plan":
        data["started"] = True
        data["current_day"] = 0
        data["xp"] = 0
        data["streak"] = 0
        data["tasks_done"] = {}
        data["extra_tasks"] = []
        save_data(data)
        day = PLAN[0]
        text = (
            f"🚀 <b>Поехали! День 1 — {day['theme']}</b>\n\n"
            + "\n".join(f"  {i+1}. {t}" for i, t in enumerate(day["tasks"]))
            + "\n\nОтмечай:"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=build_tasks_keyboard(data))

    elif query.data.startswith("task_"):
        idx = int(query.data.split("_")[1])
        key = day_tasks_key(data["current_day"])
        day = get_today_tasks(data)
        if not day:
            return
        total = len(day["tasks"])
        mask = data["tasks_done"].get(key, [False] * total)
        while len(mask) < total:
            mask.append(False)
        mask[idx] = not mask[idx]
        data["tasks_done"][key] = mask
        done_count = sum(1 for d in mask if d)
        all_done = done_count == total

        if mask[idx]:
            xp_gain = XP_PER_TASK
            data["xp"] = data.get("xp", 0) + xp_gain
            data["total_tasks_done"] = data.get("total_tasks_done", 0) + 1
            rank = get_rank(data["xp"])
            feedback = f"✅ +{xp_gain} XP! Всего: {data['xp']} | {rank}"
            if all_done:
                data["streak"] = data.get("streak", 0) + 1
                bonus = data["streak"] * STREAK_BONUS
                data["xp"] += bonus
                feedback = f"🔥 ВСЕ ЗАДАЧИ! +{xp_gain + bonus} XP (стрик x{data['streak']}) | {get_rank(data['xp'])}"
        else:
            data["xp"] = max(0, data.get("xp", 0) - XP_PER_TASK)
            data["total_tasks_done"] = max(0, data.get("total_tasks_done", 0) - 1)
            feedback = f"↩️ Отменено. XP: {data['xp']}"

        save_data(data)

        # Показываем что осталось сделать
        remaining = [day["tasks"][i] for i in range(total) if i >= len(mask) or not mask[i]]
        if remaining and not all_done:
            remaining_text = "\n\n📌 <b>Осталось сегодня:</b>\n" + "\n".join(f"• {t}" for t in remaining)
        else:
            remaining_text = ""

        header = f"📋 <b>{day['d']} — {day['theme']}</b>\n{feedback}\nВыполнено: {done_count}/{total}{remaining_text}\n"
        try:
            await query.edit_message_text(header, parse_mode="HTML", reply_markup=build_tasks_keyboard(data))
        except Exception:
            pass

        # Если все задачи закрыты — отправляем отдельное сообщение с праздником
        if all_done and mask[idx]:
            import random
            total_done_all = data.get("total_tasks_done", 0)
            total_possible = len(PLAN) * 3
            days_left = len(PLAN) - data["current_day"] - 1
            projects_closed = total_done_all // 9  # грубая оценка
            revenue_est = projects_closed * AVG_PROJECT
            to_goal = max(0, GOAL_AMOUNT - revenue_est)
            projects_to_goal = -(-to_goal // AVG_PROJECT)  # ceiling division

            celebration = random.choice(ALL_DONE_MESSAGES)
            stats = (
                f"\n\n📊 <b>Статистика к цели:</b>\n"
                f"🎯 Цель: <b>1 000 000 ₽</b> за 60 дней\n"
                f"✅ Задач закрыто всего: <b>{total_done_all}</b> из {total_possible}\n"
                f"📅 Дней пройдено: <b>{data['current_day'] + 1}/60</b>\n"
                f"💰 Расчётная выручка: ~<b>{revenue_est:,} ₽</b>\n"
                f"🏁 До цели осталось: ~<b>{to_goal:,} ₽</b> ({projects_to_goal} проектов)\n"
                f"⚡ XP: <b>{data['xp']}</b> | 🔥 Стрик: <b>{data['streak']} дней</b>"
            )
            await query.message.reply_text(celebration + stats, parse_mode="HTML")

    elif query.data == "progress":
        xp = data.get("xp", 0)
        rank = get_rank(xp)
        streak = data.get("streak", 0)
        next_thresh, next_rank = get_next_rank(xp)
        next_line = f"До {next_rank}: {next_thresh - xp} XP" if next_thresh else "Макс. ранг!"
        text = f"📊 <b>{rank}</b> | XP: {xp} | 🔥 {streak} дней\n{next_line}"
        await query.answer(text, show_alert=True)


async def send_hourly_ping(app, chat_id):
    data = load_data()
    if not data["started"]:
        return
    done_mask = get_done_mask(data)
    day = get_today_tasks(data)
    if not day:
        return
    total = len(day["tasks"])
    done_count = sum(1 for d in done_mask if d)
    if done_count == total:
        return  # все задачи уже закрыты — не беспокоим

    import random
    ping = random.choice(HOURLY_PINGS)
    remaining = [day["tasks"][i] for i in range(total) if i >= len(done_mask) or not done_mask[i]]
    remaining_text = "\n".join(f"• {t}" for t in remaining)

    text = (
        f"{ping}\n\n"
        f"📋 Осталось сегодня ({len(remaining)}/{total}):\n{remaining_text}"
    )
    await app.bot.send_message(
        chat_id=chat_id, text=text,
        parse_mode="HTML",
        reply_markup=build_tasks_keyboard(data)
    )



def main():
    if not TOKEN:
        print("Установи BOT_TOKEN в переменных окружения")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("go", go_command))
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("skip", skip_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_morning_briefing, "cron", hour=9, minute=0,
                      args=[app, OWNER_ID])
    scheduler.add_job(send_midday_check, "cron", hour=13, minute=0,
                      args=[app, OWNER_ID])
    scheduler.add_job(send_evening_report, "cron", hour=21, minute=0,
                      args=[app, OWNER_ID])
    scheduler.add_job(send_hourly_ping, "cron",
                      hour="10-20", minute=0,
                      args=[app, OWNER_ID])
    scheduler.start()

    print("Бот запущен")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
