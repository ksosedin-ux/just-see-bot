import os
import json
import logging
import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
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

# ─── ПЛАН 60 ДНЕЙ ───────────────────────────────────────────────────────────
PLAN = [
    {"d":"День 1","theme":"КП-финал","tasks":["Дожать черновик КП до финала: заполнить слайд Нового Херсонеса, проверить все цифры","Написать 3-строчный питч: кто мы, что делаем, почему нам доверяют","Сохранить КП в PDF — готово к отправке"]},
    {"d":"День 2","theme":"Соцсети-база","tasks":["Оформить шапку Instagram + VK: описание, ссылка, highlights-папки","Опубликовать вводный пост: кто такие Just See, почему MAUR набрал 4.6М","Запланировать 6 постов на 2 недели в любом планировщике"]},
    {"d":"День 3","theme":"База лидов","tasks":["Составить список 30 артистов / лейблов Москвы — у кого нет клипа или старый","Найти Instagram/TG каждого — зафиксировать в Google-таблице","Написать шаблон первого DM для артиста (2–3 строки, без шаблонщины)"]},
    {"d":"День 4","theme":"Первые касания — артисты","tasks":["Отправить 10 DM артистам по шаблону из дня 3","Опубликовать BTS-пост со съёмки (любой, даже старый материал)","Зафиксировать все отправленные в CRM: имя, канал, дата, статус"]},
    {"d":"День 5","theme":"Агентства","tasks":["Составить список 20 рекламных агентств Москвы (VK Ads, AdIndex, Telegram)","Найти ЛПР каждого — продюсер, арт-директор, аккаунт","Написать шаблон письма для агентства (субподряд-позиционирование)"]},
    {"d":"День 6","theme":"Первые касания — агентства","tasks":["Отправить 10 писем агентствам","Опубликовать Reels-тизер Cemetery of Ideas эпизод 1","Ретро дня: кто ответил, кто открыл — обновить CRM"]},
    {"d":"День 7","theme":"Ретро недели 1","tasks":["Посчитать: сколько отправлено, сколько ответов, сколько отказов","Написать 2-й follow-up тем, кто не ответил (одно предложение)","Скорректировать шаблоны — что зашло, что нет"]},
    {"d":"День 8","theme":"Контент + лиды","tasks":["Выпустить Cemetery of Ideas эпизод 1 (полный)","Отправить 15 новых DM артистам","Добавить 20 новых агентств в базу"]},
    {"d":"День 9","theme":"Тёплые касания","tasks":["Написать 3 старым клиентам — как дела + намекнуть на новые форматы","Опубликовать кейс-пост: MAUR — цифры, процесс, результат","Отправить 10 писем новым агентствам"]},
    {"d":"День 10","theme":"Лид-магнит","tasks":["Сделать PDF '3 ошибки артистов при съёмке клипа' — 1 страница","Разослать лид-магнит всем, кто ответил но не купил","Опубликовать пост-мнение: почему дешёвый клип убивает образ артиста"]},
    {"d":"День 11","theme":"Первый созвон","tasks":["Довести до звонка хотя бы 1 заинтересованного — назначить встречу","Отправить 15 новых DM/писем (микс артисты + агентства)","Обновить CRM — все статусы актуальны"]},
    {"d":"День 12","theme":"Контент","tasks":["Выпустить Cemetery of Ideas эпизод 2","Опубликовать BTS-видео или фото со съёмки","Ответить на все комментарии и DM — не игнорировать"]},
    {"d":"День 13","theme":"Встреча","tasks":["Провести 1–2 звонка/встречи с заинтересованными","После каждой встречи — отправить КП в течение 2 часов","Зафиксировать следующий шаг по каждому лиду"]},
    {"d":"День 14","theme":"Ретро фазы 1","tasks":["Итог: лидов в базе / звонков / КП отправлено / ответов","Определить: какой канал дал больше всего ответов — удвоить","Составить конкретный план фазы 2 с правками под реальность"]},
    {"d":"Дни 15–16","theme":"Разгон охвата","tasks":["Отправить 30 новых контактов за 2 дня (15 в день)","Провести 2 звонка с тёплыми из фазы 1","Выпустить Cemetery of Ideas эпизод 3"]},
    {"d":"Дни 17–18","theme":"Дожим","tasks":["Follow-up всем, кто получил КП но не ответил — звонок или голосовое","Опубликовать кейс РФА: что сняли, зачем, результат","Добавить 30 новых контактов в базу"]},
    {"d":"Дни 19–21","theme":"Встречи","tasks":["Провести 3–4 встречи / звонка за 3 дня","После каждой — конкретный следующий шаг","Опубликовать 2 поста: BTS + мнение о рынке"]},
    {"d":"Дни 22–24","theme":"Контент-волна","tasks":["Выпустить эпизоды 4 и 5 Cemetery of Ideas","Опубликовать отзыв от любого клиента","Запустить таргет VK: бюджет 3–5 тыс. руб., ведёт на профиль"]},
    {"d":"Дни 25–28","theme":"Закрытие первого","tasks":["Цель — подписать 1 договор. Предложи мини-формат или пилот","Собрать 3 отзыва от прошлых клиентов — оформить в пост","Расширить базу до 100+ контактов"]},
    {"d":"Дни 29–31","theme":"Новая волна","tasks":["Отправить 40 новых холодных (малый бизнес, кафе, бренды одежды)","Выпустить Cemetery of Ideas эпизоды 6–7","Провести 4–5 звонков за 3 дня"]},
    {"d":"Дни 32–35","theme":"Ретро фазы 2","tasks":["Итог: договоров / встреч / лидов / лучший канал","Скорректировать оффер — что чаще всего отталкивало клиентов","Записать Reels с итогами первого месяца продакшена"]},
    {"d":"Дни 36–38","theme":"Работа с тёплыми","tasks":["Перейти только на тёплых — холодную рассылку делегировать","Провести 3 встречи с наиболее горячими лидами","Выпустить эпизоды 8–9 Cemetery of Ideas"]},
    {"d":"Дни 39–42","theme":"Второй договор","tasks":["Закрыть 2-й договор","Запустить производство — фиксировать процесс для контента","Запустить реферальную программу: попроси каждого клиента назвать 1–2 контакта"]},
    {"d":"Дни 43–46","theme":"Новая ниша","tasks":["Отправить 30 писем в новую нишу (event-агентства, музыкальные школы)","Опубликовать 3 поста: кейс + BTS + мнение","Сделать апселл действующему клиенту — доп. формат или ролик"]},
    {"d":"Дни 47–50","theme":"Третий договор","tasks":["Закрыть 3-й договор","Выпустить финальные эпизоды Cemetery of Ideas + анонс сезона 2","Обновить КП с новыми кейсами и цифрами"]},
    {"d":"Дни 51–55","theme":"Анализ и система","tasks":["Что работало лучше всего — канал, тип клиента, оффер? Зафиксировать","Написать скрипт для Жени или фрилансера на типовые продажи","Опубликовать Reels с итогами 2 месяцев"]},
    {"d":"Дни 56–60","theme":"Планирование месяц 3","tasks":["Финальный ретро: выручка, лиды, договоры, подписчики","Поставить цели на следующие 60 дней с новыми данными","Запустить следующий цикл — теперь с опытом и базой"]},
]

# ─── КОНСТАНТЫ ───────────────────────────────────────────────────────────────
GOAL_AMOUNT = 1_000_000
AVG_PROJECT = 80_000
XP_PER_TASK = 100
STREAK_BONUS = 50

RANKS = [
    (0,     "🎬 Новичок"),
    (500,   "📹 Оператор"),
    (1500,  "🎥 Режиссёр"),
    (3000,  "⭐ Продюсер"),
    (6000,  "🏆 Топ-продакшен"),
    (10000, "👑 Just See Legend"),
]

# ─── ДОСТИЖЕНИЯ ──────────────────────────────────────────────────────────────
ACHIEVEMENTS = [
    {"id":"first_lead",     "name":"🎯 Первый лид",           "desc":"Добавил первого лида в CRM"},
    {"id":"first_deal",     "name":"💰 Первая сделка Just See","desc":"Зафиксировал первую оплату"},
    {"id":"streak_3",       "name":"🔥 3 дня подряд",          "desc":"Стрик 3 дня"},
    {"id":"streak_7",       "name":"⚡ Неделя без остановки",  "desc":"Стрик 7 дней"},
    {"id":"streak_14",      "name":"💎 Машина Just See",       "desc":"Стрик 14 дней"},
    {"id":"leads_10",       "name":"📋 Десятка лидов",         "desc":"10 лидов в базе"},
    {"id":"leads_50",       "name":"🚀 Мастер холодных",       "desc":"50 лидов в базе"},
    {"id":"leads_100",      "name":"👑 База сотни",            "desc":"100 лидов в базе"},
    {"id":"deals_3",        "name":"🎬 Продакшен работает",    "desc":"3 закрытых сделки"},
    {"id":"half_goal",      "name":"💸 Полпути к миллиону",    "desc":"500 000 ₽ оборота"},
    {"id":"goal_reached",   "name":"🏆 МИЛЛИОНЕР Just See",    "desc":"1 000 000 ₽ оборота"},
    {"id":"tasks_30",       "name":"✅ 30 задач закрыто",       "desc":"Тридцатка задач"},
    {"id":"tasks_90",       "name":"💪 90 задач — месяц пашешь","desc":"Девяностка задач"},
    {"id":"win_logged",     "name":"🌟 Первая победа",         "desc":"Записал первую победу в дневник"},
    {"id":"content_5",      "name":"📱 Контент-машина",        "desc":"5 постов опубликовано"},
    {"id":"project_done",   "name":"🎥 Проект сдан",           "desc":"Первый проект доведён до оплаты"},
]

# ─── ЕЖЕДНЕВНЫЕ ЧЕЛЛЕНДЖИ ────────────────────────────────────────────────────
DAILY_CHALLENGES = [
    {"type":"sales",   "text":"Отправь 5 холодных сообщений сегодня",     "xp":200},
    {"type":"sales",   "text":"Сделай 1 звонок до обеда",                 "xp":150},
    {"type":"sales",   "text":"Напиши follow-up 3 зависшим лидам",        "xp":150},
    {"type":"content", "text":"Опубликуй 1 пост или Reels сегодня",       "xp":150},
    {"type":"content", "text":"Ответь на все DM и комментарии",            "xp":100},
    {"type":"streak",  "text":"Закрой все 3 задачи — сохрани стрик",      "xp":200},
    {"type":"streak",  "text":"Начни день до 10:00 — открой бота утром",  "xp":100},
    {"type":"sales",   "text":"Добавь 3 новых контакта в базу",           "xp":100},
]

# ─── КАРТОЧКИ ОБУЧЕНИЯ ───────────────────────────────────────────────────────
LEARNING_CARDS = [
    {"topic":"💼 Продажи","title":"Правило 48 часов","text":"После любого контакта с лидом — следующий шаг в течение 48 часов. Дольше = остываешь ты и он. Поставь напоминание сразу после звонка."},
    {"topic":"💼 Продажи","title":"Продавай результат, не процесс","text":"Клиенту не важно сколько камер и какой монтаж. Ему важно: клип даст подписчиков, реклама даст продажи. Говори о результате первым."},
    {"topic":"💼 Продажи","title":"Возражение — это вопрос","text":"'Дорого' = 'Не понимаю за что плачу'. 'Подумаю' = 'Не убедил'. Не спорь — уточняй: 'Что именно смущает?'"},
    {"topic":"💼 Продажи","title":"Follow-up решает всё","text":"80% сделок закрываются после 5-го касания. Большинство сдаются после первого. Отправь второе письмо — ты уже впереди конкурентов."},
    {"topic":"💼 Продажи","title":"Социальное доказательство","text":"Перед КП упомяни: 'Наш клип для артиста набрал 4.6М'. Один конкретный результат убеждает лучше любого описания услуг."},
    {"topic":"💼 Продажи","title":"Цена — последней","text":"Называй цену только после того как клиент понял ценность. Порядок: результат → кейсы → процесс → цена. Не наоборот."},
    {"topic":"💼 Продажи","title":"Дедлайн создаёт решение","text":"'Можем взять ваш проект на март' работает лучше чем 'когда удобно'. Мягкий дедлайн помогает клиенту принять решение."},
    {"topic":"💼 Продажи","title":"Один вопрос после отказа","text":"Клиент отказал — спроси: 'Что должно было быть иначе чтобы вы согласились?' Это лучший источник знаний о рынке."},
    {"topic":"📱 Маркетинг","title":"Контент = доверие заранее","text":"Клиент видит Reels → понимает как ты думаешь → приходит готовым. Контент продаёт пока ты снимаешь. 1 пост = 1 касание с рынком."},
    {"topic":"📱 Маркетинг","title":"Первые 3 секунды решают","text":"Если не зацепил в начале Reels — не досмотрят. Начинай с конфликта, вопроса или неожиданного факта. Не с приветствия."},
    {"topic":"📱 Маркетинг","title":"Ниша внутри ниши","text":"'Видеопродакшен' — широко. 'Клипы для артистов 50к+ подписчиков' — точно. Чем уже позиционирование, тем легче найти нужных клиентов."},
    {"topic":"📱 Маркетинг","title":"Кейс сильнее рекламы","text":"Пост 'сняли клип → результат X' продаёт лучше любого рекламного текста. Документируй каждый проект: до/после, цифры, процесс."},
    {"topic":"📱 Маркетинг","title":"BTS стоит 0 рублей","text":"За кулисами съёмки — контент который показывает экспертизу и стоит 0. Снимай телефоном прямо во время работы."},
    {"topic":"🎬 Продакшен","title":"Бриф спасает проект","text":"90% конфликтов — несовпадение ожиданий. Подробный бриф до начала = меньше правок, быстрая сдача, довольный клиент."},
    {"topic":"🎬 Продакшен","title":"Правки — не бесплатно","text":"Пропиши в договоре: 2 круга правок включены, далее почасовая оплата. Это защита твоего времени, не жадность."},
    {"topic":"🎬 Продакшен","title":"Предоплата обязательна","text":"Минимум 50% до старта. Без предоплаты клиент не ценит твоё время и легко отменяет. Деньги = серьёзность."},
    {"topic":"🎬 Продакшен","title":"Дедлайн с запасом","text":"Называй клиенту дедлайн на 3-5 дней позже реального. Сдашь раньше — выглядишь героем."},
    {"topic":"🎬 Продакшен","title":"Сначала деньги, потом файлы","text":"Финальные файлы — только после полной оплаты. Всегда. Это стандарт индустрии, не недоверие."},
    {"topic":"⚡ Эффективность","title":"Съедай лягушку утром","text":"Самая неприятная задача — первой. Пока энергия есть. Холодный звонок в 9:00 лучше чем в 18:00."},
    {"topic":"⚡ Эффективность","title":"Один приоритет дня","text":"Если сделаю только одно — что это? Запиши утром. Всё остальное бонус. Фокус на главном даёт результат быстрее чем 10 задач по чуть-чуть."},
    {"topic":"⚡ Эффективность","title":"Группируй похожие задачи","text":"Все звонки — один блок. Все письма — другой. Переключение между типами задач съедает до 40% времени."},
    {"topic":"⚡ Эффективность","title":"Система важнее мотивации","text":"Мотивация кончается. Система — нет. Одно и то же каждый день в одно время — уже не усилие, а привычка."},
    {"topic":"💰 Деньги","title":"Поднимай цены раз в полгода","text":"Ты растёшь — цены должны расти. +15-20% раз в 6 месяцев — норма. Клиенты которые уходят из-за цены — не твои клиенты."},
    {"topic":"💰 Деньги","title":"Апселл проще нового клиента","text":"Продать доп. услугу клиенту в 7 раз проще чем найти нового. После сдачи: 'Хотите вертикальный формат для Stories?'"},
    {"topic":"💰 Деньги","title":"Считай час своей работы","text":"Месячный доход ÷ рабочие часы = твоя ставка. Если задача стоит дешевле ставки — делегируй. Дороже — берись сам."},
    {"topic":"💰 Деньги","title":"Подписка вместо разовых","text":"'2 клипа в месяц за фиксированную сумму' = стабильный доход. Один клиент на подписке = 12 проектов в год без поиска."},
]

# ─── ВОПРОСЫ РЕФЛЕКСИИ ───────────────────────────────────────────────────────
REFLECTION_QUESTIONS = [
    "Что на этой неделе сработало лучше всего в продажах или производстве?",
    "Что не получилось — честно, без оправданий. Почему?",
    "Какой урок недели изменит следующую неделю?",
    "Что ты откладывал всю неделю и так и не сделал — почему?",
    "Что одно ты сделаешь иначе на следующей неделе?",
]


# ─── ГЛАВНОЕ МЕНЮ ────────────────────────────────────────────────────────────
def get_main_menu():
    keyboard = [
        [KeyboardButton("📋 Задачи"), KeyboardButton("📊 Прогресс"), KeyboardButton("💰 Финансы")],
        [KeyboardButton("👥 CRM"), KeyboardButton("🎬 Проекты"), KeyboardButton("📱 Контент")],
        [KeyboardButton("🏆 Достижения"), KeyboardButton("🎯 Цели"), KeyboardButton("📚 Учиться")],
        [KeyboardButton("🌟 Победы"), KeyboardButton("⚡ Челлендж"), KeyboardButton("🪞 Рефлексия")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

MORNING_QUOTES = [
    "Продакшены не строятся пока ты спишь. Но план уже готов 💪",
    "Клиенты не придут сами. Зато 3 задачи сегодня приблизят тебя к этому.",
    "MAUR набрал 4.6М. Следующий рекорд начинается сегодня.",
    "Один час утром на продажи = одна неделя не в ноль.",
    "Сегодня ты строишь то, что через 2 месяца будет работать само.",
    "Just See не стоит на месте. Движение = результат.",
    "Каждый лид сегодня — это потенциальный договор на следующей неделе.",
]

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

# ─── ДАННЫЕ ──────────────────────────────────────────────────────────────────
def load_data():
    if Path(DATA_FILE).exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {
        "started": False,
        "current_day": 0,
        "tasks_done": {},
        "extra_tasks": [],
        "xp": 0,
        "streak": 0,
        "last_active": None,
        "total_tasks_done": 0,
        "achievements": [],
        # CRM
        "leads": [],
        # Финансы
        "deals": [],          # {name, amount, cost, type, date, status}
        # Проекты
        "projects": [],       # {name, client, stage, budget, deadline, paid}
        # Контент-план
        "content": [],        # {idea, platform, status, date}
        # Победы
        "wins": [],
        # Цели недели
        "weekly_goals": [],
        "weekly_goals_done": [],
        # Продуктивность
        "energy_log": [],     # [{date, energy}]
        "daily_focus": [],    # [{date, focus}]
        # Помодоро
        "pomodoro_active": False,
        "pomodoro_end": None,
        # Режим тишины
        "quiet_until": None,
        # Съёмочный день
        "shoot_mode": False,
        # Ежедневный челлендж
        "daily_challenge": None,
        "challenge_done": False,
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ─── ВСПОМОГАТЕЛЬНЫЕ ─────────────────────────────────────────────────────────
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
    return data["tasks_done"].get(str(data["current_day"]), [])

def build_tasks_keyboard(data):
    day = get_today_tasks(data)
    if not day:
        return None
    done_mask = get_done_mask(data)
    keyboard = []
    for i, task in enumerate(day["tasks"]):
        done = i < len(done_mask) and done_mask[i]
        emoji = "✅" if done else "⬜"
        short = task[:38] + "…" if len(task) > 38 else task
        keyboard.append([InlineKeyboardButton(f"{emoji} {short}", callback_data=f"task_{i}")])
    keyboard.append([
        InlineKeyboardButton("📊 Прогресс", callback_data="progress"),
        InlineKeyboardButton("💰 Финансы", callback_data="finance_quick"),
    ])
    return InlineKeyboardMarkup(keyboard)

def check_achievements(data, app=None, chat_id=None):
    """Проверяем и выдаём новые достижения"""
    earned = data.get("achievements", [])
    new_ones = []

    leads_count = len(data.get("leads", []))
    deals = data.get("deals", [])
    total_revenue = sum(d.get("amount", 0) for d in deals if d.get("status") == "оплачен")
    total_tasks = data.get("total_tasks_done", 0)
    wins_count = len(data.get("wins", []))
    content_done = len([c for c in data.get("content", []) if c.get("status") == "опубликован"])
    streak = data.get("streak", 0)
    deals_closed = len([d for d in deals if d.get("status") == "оплачен"])

    checks = {
        "first_lead":   leads_count >= 1,
        "first_deal":   deals_closed >= 1,
        "streak_3":     streak >= 3,
        "streak_7":     streak >= 7,
        "streak_14":    streak >= 14,
        "leads_10":     leads_count >= 10,
        "leads_50":     leads_count >= 50,
        "leads_100":    leads_count >= 100,
        "deals_3":      deals_closed >= 3,
        "half_goal":    total_revenue >= 500_000,
        "goal_reached": total_revenue >= 1_000_000,
        "tasks_30":     total_tasks >= 30,
        "tasks_90":     total_tasks >= 90,
        "win_logged":   wins_count >= 1,
        "content_5":    content_done >= 5,
        "project_done": deals_closed >= 1,
    }

    for ach in ACHIEVEMENTS:
        if ach["id"] not in earned and checks.get(ach["id"], False):
            earned.append(ach["id"])
            new_ones.append(ach)

    data["achievements"] = earned
    return new_ones

def finance_summary(data):
    deals = data.get("deals", [])
    revenue = sum(d.get("amount", 0) for d in deals if d.get("status") == "оплачен")
    pending = sum(d.get("amount", 0) for d in deals if d.get("status") == "ожидается")
    potential = sum(d.get("amount", 0) for d in deals if d.get("status") == "переговоры")
    total_cost = sum(d.get("cost", 0) for d in deals if d.get("status") == "оплачен")
    profit = revenue - total_cost

    clips_rev = sum(d.get("amount",0) for d in deals if d.get("type")=="клип" and d.get("status")=="оплачен")
    ads_rev   = sum(d.get("amount",0) for d in deals if d.get("type")=="реклама" and d.get("status")=="оплачен")
    sub_rev   = sum(d.get("amount",0) for d in deals if d.get("type")=="субподряд" and d.get("status")=="оплачен")

    # Прогноз по темпу
    day_num = max(data.get("current_day", 1), 1)
    daily_rate = revenue / day_num if day_num > 0 else 0
    days_to_goal = int((GOAL_AMOUNT - revenue) / daily_rate) if daily_rate > 0 else 999

    to_goal = max(0, GOAL_AMOUNT - revenue)
    pct = min(100, int(revenue / GOAL_AMOUNT * 100))
    bar_f = int(pct / 10)
    bar = "█" * bar_f + "░" * (10 - bar_f)

    return (
        f"💰 <b>Финансы Just See</b>\n\n"
        f"<b>Оборот:</b> {revenue:,} ₽\n"
        f"<b>Чистая прибыль:</b> {profit:,} ₽\n"
        f"<b>Ожидается:</b> {pending:,} ₽\n"
        f"<b>В переговорах:</b> {potential:,} ₽\n\n"
        f"<b>По типам:</b>\n"
        f"  🎬 Клипы: {clips_rev:,} ₽\n"
        f"  📺 Реклама: {ads_rev:,} ₽\n"
        f"  🤝 Субподряд: {sub_rev:,} ₽\n\n"
        f"<b>Цель 1 000 000 ₽:</b>\n"
        f"[{bar}] {pct}%\n"
        f"Осталось: {to_goal:,} ₽\n"
        f"📈 Прогноз: {'достигнешь через ' + str(days_to_goal) + ' дней' if daily_rate > 0 else 'нет данных для прогноза'}"
    )

def funnel_summary(data):
    leads = data.get("leads", [])
    cold =    len([l for l in leads if l.get("status") == "холодный"])
    warm =    len([l for l in leads if l.get("status") == "тёплый"])
    nego =    len([l for l in leads if l.get("status") == "переговоры"])
    contract= len([l for l in leads if l.get("status") == "договор"])
    working = len([l for l in leads if l.get("status") == "в работе"])
    closed =  len([l for l in leads if l.get("status") == "закрыт"])
    total = len(leads)

    # Конверсии
    c1 = f"{int(warm/cold*100)}%" if cold > 0 else "–"
    c2 = f"{int(nego/warm*100)}%" if warm > 0 else "–"
    c3 = f"{int(contract/nego*100)}%" if nego > 0 else "–"

    # Рекомендация
    rec = ""
    if cold > 20 and warm < 3:
        rec = "\n💡 Мало тёплых — улучши шаблон первого касания"
    elif warm > 5 and nego < 2:
        rec = "\n💡 Тёплые зависают — пора звонить, не писать"
    elif nego > 3 and contract < 1:
        rec = "\n💡 Много переговоров без договора — снизь порог входа"
    else:
        rec = "\n💡 Воронка в норме — наращивай объём холодных"

    return (
        f"🔽 <b>Воронка продаж</b>\n\n"
        f"❄️ Холодный: {cold}\n"
        f"   ↓ конверсия {c1}\n"
        f"🌡 Тёплый: {warm}\n"
        f"   ↓ конверсия {c2}\n"
        f"💬 Переговоры: {nego}\n"
        f"   ↓ конверсия {c3}\n"
        f"📝 Договор: {contract}\n"
        f"🎬 В работе: {working}\n"
        f"✅ Закрыт: {closed}\n\n"
        f"Всего в базе: {total}"
        f"{rec}"
    )

# ─── РАССЫЛКИ ────────────────────────────────────────────────────────────────
async def send_morning_briefing(app, chat_id):
    data = load_data()
    if not data["started"]:
        return
    if data.get("quiet_until") and datetime.now().isoformat() < data["quiet_until"]:
        return

    day = get_today_tasks(data)
    if not day:
        return

    # Генерируем ежедневный челлендж
    challenge = random.choice(DAILY_CHALLENGES)
    data["daily_challenge"] = challenge
    data["challenge_done"] = False

    # Утренний вопрос о фокусе
    quote = random.choice(MORNING_QUOTES)

    # Карточка обучения
    card = random.choice(LEARNING_CARDS)
    learning_line = f"\n\n📚 <b>Карточка дня — {card['topic']}</b>\n<b>{card['title']}</b>\n{card['text']}"
    day_num = data["current_day"] + 1
    rank = get_rank(data["xp"])
    streak = data["streak"]
    streak_line = f"🔥 Стрик: {streak} дней подряд" if streak > 0 else "Начни стрик сегодня!"

    # Зависшие лиды
    leads = data.get("leads", [])
    stale_leads = []
    for l in leads:
        if l.get("last_contact"):
            days_ago = (datetime.now() - datetime.fromisoformat(l["last_contact"])).days
            if days_ago >= 3 and l.get("status") not in ["закрыт", "оплачен"]:
                stale_leads.append(l)
    stale_line = ""
    if stale_leads[:3]:
        stale_line = "\n\n⚠️ <b>Дожать сегодня:</b>\n" + "\n".join(f"• {l['name']} ({l.get('status','?')})" for l in stale_leads[:3])

    # Проекты с дедлайнами
    projects = data.get("projects", [])
    urgent = []
    for p in projects:
        if p.get("deadline") and p.get("stage") not in ["оплачен"]:
            try:
                dl = datetime.fromisoformat(p["deadline"])
                days_left = (dl - datetime.now()).days
                if days_left <= 3:
                    urgent.append(f"• {p['name']} — через {days_left} дн.")
            except:
                pass
    urgent_line = ""
    if urgent:
        urgent_line = "\n\n🚨 <b>Дедлайны горят:</b>\n" + "\n".join(urgent)

    # Контент на сегодня
    content = data.get("content", [])
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_content = [c for c in content if c.get("date") == today_str and c.get("status") != "опубликован"]
    content_line = ""
    if today_content:
        content_line = "\n\n📱 <b>Контент сегодня:</b>\n" + "\n".join(f"• {c['idea']} ({c.get('platform','')})" for c in today_content[:2])

    extra = data.get("extra_tasks", [])
    extra_line = f"\n\n⏭ <b>Перенесено с вчера ({len(extra)}):</b>\n" + "\n".join(f"• {t}" for t in extra) if extra else ""

    tasks_text = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(day["tasks"]))

    text = (
        f"☀️ <b>Доброе утро, Кирилл!</b>\n\n"
        f"<i>{quote}</i>\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📅 <b>{day['d']} — {day['theme']}</b>\n"
        f"{rank} | XP: {data['xp']} | {streak_line}\n"
        f"━━━━━━━━━━━━━━━"
        f"{extra_line}"
        f"{stale_line}"
        f"{urgent_line}"
        f"{content_line}\n\n"
        f"<b>Задачи на сегодня:</b>\n{tasks_text}\n\n"
        f"⚡ <b>Челлендж дня:</b> {challenge['text']} (+{challenge['xp']} XP)"
        f"{learning_line}\n\n"
        f"Отмечай по мере выполнения 👇"
    )
    save_data(data)
    await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML",
                               reply_markup=build_tasks_keyboard(data))

    # Запрашиваем энергию
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(str(i), callback_data=f"energy_{i}") for i in range(1, 6)
    ],[
        InlineKeyboardButton(str(i), callback_data=f"energy_{i}") for i in range(6, 11)
    ]])
    await app.bot.send_message(chat_id=chat_id,
        text="⚡ <b>Как твоя энергия сегодня?</b> (1–10)",
        parse_mode="HTML", reply_markup=kb)


async def send_midday_check(app, chat_id):
    data = load_data()
    if not data["started"]:
        return
    if data.get("quiet_until") and datetime.now().isoformat() < data["quiet_until"]:
        return
    done_mask = get_done_mask(data)
    done_count = sum(1 for d in done_mask if d)
    day = get_today_tasks(data)
    if not day:
        return
    total = len(day["tasks"])
    if done_count == 0:
        msg = "⚡ <b>Дневная проверка</b>\n\nЕщё ни одной задачи. Один час сейчас = прогресс Just See. Погнали?"
    elif done_count == total:
        msg = f"🏆 <b>Дневная проверка</b>\n\nВсе {total} задачи до обеда! Красавчик."
    else:
        left = total - done_count
        msg = f"💪 <b>Дневная проверка</b>\n\nСделано {done_count}/{total}. Осталось {left} — это максимум 30 минут."
    await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML",
                               reply_markup=build_tasks_keyboard(data))


async def send_hourly_ping(app, chat_id):
    data = load_data()
    if not data["started"]:
        return
    if data.get("quiet_until") and datetime.now().isoformat() < data["quiet_until"]:
        return
    if data.get("shoot_mode"):
        return
    done_mask = get_done_mask(data)
    day = get_today_tasks(data)
    if not day:
        return
    total = len(day["tasks"])
    done_count = sum(1 for d in done_mask if d)
    if done_count == total:
        return
    remaining = [day["tasks"][i] for i in range(total) if i >= len(done_mask) or not done_mask[i]]
    ping = random.choice(HOURLY_PINGS)
    text = f"{ping}\n\n📋 Осталось ({len(remaining)}/{total}):\n" + "\n".join(f"• {t}" for t in remaining)
    await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML",
                               reply_markup=build_tasks_keyboard(data))


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

    # Проверяем достижения
    new_achs = check_achievements(data)

    rank = get_rank(data["xp"])
    next_thresh, next_rank = get_next_rank(data["xp"])
    pct_tasks = int(done_count / total * 100) if total > 0 else 0
    bar_f = int(pct_tasks / 10)
    bar = "█" * bar_f + "░" * (10 - bar_f)

    # Финансовая сводка
    deals = data.get("deals", [])
    revenue = sum(d.get("amount", 0) for d in deals if d.get("status") == "оплачен")
    pending = sum(d.get("amount", 0) for d in deals if d.get("status") == "ожидается")
    profit = revenue - sum(d.get("cost", 0) for d in deals if d.get("status") == "оплачен")
    to_goal = max(0, GOAL_AMOUNT - revenue)
    goal_pct = min(100, int(revenue / GOAL_AMOUNT * 100))
    goal_bar_f = int(goal_pct / 10)
    goal_bar = "█" * goal_bar_f + "░" * (10 - goal_bar_f)

    # Воронка кратко
    leads = data.get("leads", [])
    warm = len([l for l in leads if l.get("status") in ["тёплый","переговоры","договор"]])
    cold = len([l for l in leads if l.get("status") == "холодный"])

    # Энергия дня
    energy_log = data.get("energy_log", [])
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_energy = next((e["energy"] for e in energy_log if e["date"] == today_str), None)
    energy_line = f"\n⚡ Энергия дня: {today_energy}/10" if today_energy else ""

    # Фокус дня
    daily_focus = data.get("daily_focus", [])
    today_focus = next((f["focus"] for f in daily_focus if f["date"] == today_str), None)
    focus_line = f"\n🎯 Фокус дня: {today_focus}" if today_focus else ""

    # Челлендж
    challenge = data.get("daily_challenge")
    ch_done = data.get("challenge_done", False)
    ch_line = ""
    if challenge:
        ch_icon = "✅" if ch_done else "❌"
        ch_line = f"\n{ch_icon} Челлендж: {challenge['text']}"

    failed_line = ""
    if failed_tasks:
        failed_line = "\n\n⏭ <b>Переносим на завтра:</b>\n" + "\n".join(f"• {t}" for t in failed_tasks)
        data["extra_tasks"] = failed_tasks
    else:
        data["extra_tasks"] = []

    next_rank_line = f"\n🎯 До <b>{next_rank}</b>: {next_thresh - data['xp']} XP" if next_thresh else ""

    verdict = random.choice(["🔥 Все три! Серьёзный человек.","💎 День закрыт чисто.","⚡ Именно так строятся продакшены."]) if done_count == total else random.choice(["Не всё сделано — завтра берёшь реванш.","Производство сожрало день? Завтра — сначала продажи."])

    text = (
        f"🌙 <b>ИТОГ ДНЯ — {day['d']}</b>\n\n"
        f"{verdict}\n\n"

        f"━━━ 📋 ЗАДАЧИ ━━━\n"
        f"[{bar}] {done_count}/{total} ({pct_tasks}%)\n"
        f"💰 XP за день: +{xp_earned}\n"
        f"⚡ Всего XP: {data['xp']}\n"
        f"🏅 Ранг: {rank}\n"
        f"🔥 Стрик: {data['streak']} дней"
        f"{next_rank_line}"
        f"{ch_line}"
        f"{energy_line}"
        f"{focus_line}\n\n"

        f"━━━ 💰 ФИНАНСЫ ━━━\n"
        f"Оборот: <b>{revenue:,} ₽</b>\n"
        f"Прибыль: <b>{profit:,} ₽</b>\n"
        f"Ожидается: {pending:,} ₽\n"
        f"[{goal_bar}] {goal_pct}% к миллиону\n"
        f"Осталось: {to_goal:,} ₽\n\n"

        f"━━━ 🎯 ВОРОНКА ━━━\n"
        f"Лидов всего: {len(leads)} | Тёплых: {warm} | Холодных: {cold}\n\n"

        f"━━━ 📅 ЗАВТРА ━━━\n"
        f"<b>{PLAN[min(data['current_day']+1, len(PLAN)-1)]['d']}: "
        f"{PLAN[min(data['current_day']+1, len(PLAN)-1)]['theme']}</b>"
        f"{failed_line}"
    )

    data["current_day"] = min(data["current_day"] + 1, len(PLAN) - 1)
    data["last_active"] = datetime.now().isoformat()
    data["shoot_mode"] = False
    save_data(data)

    await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")

    # Достижения
    for ach in new_achs:
        await app.bot.send_message(chat_id=chat_id,
            text=f"🏆 <b>ДОСТИЖЕНИЕ РАЗБЛОКИРОВАНО!</b>\n\n{ach['name']}\n<i>{ach['desc']}</i>",
            parse_mode="HTML")


async def send_weekly_report(app, chat_id):
    data = load_data()
    if not data["started"]:
        return

    # Задачи за неделю
    current = data["current_day"]
    week_start = max(0, current - 7)
    week_done = 0
    week_total = 0
    for i in range(week_start, current):
        mask = data["tasks_done"].get(str(i), [])
        week_done += sum(1 for d in mask if d)
        if i < len(PLAN):
            week_total += len(PLAN[i]["tasks"])

    # Финансы
    deals = data.get("deals", [])
    revenue = sum(d.get("amount",0) for d in deals if d.get("status")=="оплачен")
    pending = sum(d.get("amount",0) for d in deals if d.get("status")=="ожидается")
    profit = revenue - sum(d.get("cost",0) for d in deals if d.get("status")=="оплачен")
    to_goal = max(0, GOAL_AMOUNT - revenue)

    # Воронка
    leads = data.get("leads", [])
    funnel = funnel_summary(data)

    # Продуктивность
    energy_log = data.get("energy_log", [])
    if energy_log:
        avg_energy = sum(e["energy"] for e in energy_log[-7:]) / len(energy_log[-7:])
        energy_line = f"⚡ Средняя энергия за неделю: {avg_energy:.1f}/10"
    else:
        energy_line = "⚡ Энергия не отслеживалась"

    # Цели недели
    goals = data.get("weekly_goals", [])
    goals_done = data.get("weekly_goals_done", [])
    goals_line = ""
    if goals:
        goals_line = "\n\n━━━ 🎯 ЦЕЛИ НЕДЕЛИ ━━━\n"
        for g in goals:
            icon = "✅" if g in goals_done else "❌"
            goals_line += f"{icon} {g}\n"

    # Победы за неделю
    wins = data.get("wins", [])
    week_wins = wins[-5:] if wins else []
    wins_line = ""
    if week_wins:
        wins_line = "\n\n━━━ 🌟 ПОБЕДЫ НЕДЕЛИ ━━━\n" + "\n".join(f"• {w['text']}" for w in week_wins)

    # Рекомендация
    eff = int(week_done/week_total*100) if week_total > 0 else 0
    if eff < 50:
        rec = "⚠️ Меньше половины задач. Главная проблема — начать. Ставь будильник на продажи."
    elif eff < 80:
        rec = "💪 Хороший темп. Ещё чуть-чуть — и будет стабильный результат."
    else:
        rec = "🔥 Отличная неделя! Держи темп — это и есть система."

    text = (
        f"📊 <b>НЕДЕЛЬНЫЙ ОТЧЁТ Just See</b>\n\n"
        f"━━━ 📋 ЗАДАЧИ ━━━\n"
        f"Выполнено: {week_done}/{week_total} ({eff}%)\n"
        f"XP всего: {data['xp']} | Ранг: {get_rank(data['xp'])}\n"
        f"🔥 Стрик: {data['streak']} дней\n"
        f"{energy_line}\n\n"

        f"━━━ 💰 ФИНАНСЫ ━━━\n"
        f"Оборот: <b>{revenue:,} ₽</b>\n"
        f"Прибыль: <b>{profit:,} ₽</b>\n"
        f"Ожидается: {pending:,} ₽\n"
        f"До цели 1 млн: {to_goal:,} ₽\n\n"

        f"{funnel}"
        f"{goals_line}"
        f"{wins_line}\n\n"

        f"━━━ 💡 ВЫВОД ━━━\n"
        f"{rec}"
    )

    # Сбрасываем цели недели
    data["weekly_goals"] = []
    data["weekly_goals_done"] = []
    save_data(data)

    await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")

    # Запрашиваем цели на следующую неделю
    await app.bot.send_message(chat_id=chat_id,
        text="🎯 <b>Цели на следующую неделю</b>\n\nНапиши 1–3 главные цели на неделю.\nПример: <i>Закрыть 2 договора, выпустить 2 Reels, набрать 20 новых лидов</i>",
        parse_mode="HTML")


async def send_finance_weekly(app, chat_id):
    data = load_data()
    if not data["started"]:
        return
    text = finance_summary(data)
    await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")



# ─── РЕФЛЕКСИЯ И ОБУЧЕНИЕ ────────────────────────────────────────────────────
async def send_reflection(app, chat_id):
    """Воскресная рефлексия — 5 вопросов по одному"""
    data = load_data()
    if not data["started"]:
        return
    await app.bot.send_message(
        chat_id=chat_id,
        text=(
            "🪞 <b>Время рефлексии, босс</b>\n\n"
            "Каждое воскресенье — 5 вопросов которые делают следующую неделю лучше.\n"
            "Отвечай честно, коротко. Это только для тебя.\n\n"
            "Сохраняю ответы в дневник — потом можно перечитать и увидеть рост."
        ),
        parse_mode="HTML"
    )
    data["reflection_pending"] = list(range(len(REFLECTION_QUESTIONS)))
    data["reflection_answers"] = []
    data["reflection_q_idx"] = 0
    save_data(data)
    await app.bot.send_message(
        chat_id=chat_id,
        text=f"❓ <b>Вопрос 1 из 5:</b>\n\n{REFLECTION_QUESTIONS[0]}",
        parse_mode="HTML"
    )


async def send_learn_card(app, chat_id):
    """Ежедневная карточка обучения (отдельная команда)"""
    card = random.choice(LEARNING_CARDS)
    text = (
        f"📚 <b>{card['topic']} — {card['title']}</b>\n\n"
        f"{card['text']}\n\n"
        f"<i>Применить сегодня?</i>"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Применю сегодня +50 XP", callback_data="learn_apply"),
        InlineKeyboardButton("📖 Ещё карточку", callback_data="learn_next"),
    ]])
    await app.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=kb)



# ─── КОМАНДЫ ─────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎬 <b>Just See Production — Бот роста</b>\n\n"
        "Твой персональный ассистент продакшена.\n\n"
        "<b>Задачи:</b>\n"
        "/go — запустить план\n"
        "/tasks — задачи сегодня\n"
        "/progress — прогресс и ранг\n"
        "/stats — история дней\n"
        "/skip — пропустить день\n"
        "/shoot — режим съёмки (тишина)\n"
        "/quiet N — тишина на N часов\n"
        "/focus Текст — главная цель дня\n"
        "/win Текст — записать победу\n"
        "/wins — дневник побед\n\n"
        "<b>CRM:</b>\n"
        "/crm — все лиды\n"
        "/funnel — воронка продаж\n"
        "лид Имя, канал — добавить лида\n"
        "/status Имя статус — обновить статус\n\n"
        "<b>Финансы:</b>\n"
        "/finance — сводка\n"
        "сделка Имя, сумма, расходы, тип — добавить\n\n"
        "<b>Проекты:</b>\n"
        "/projects — все проекты\n"
        "проект Название, клиент, дедлайн — добавить\n\n"
        "<b>Контент:</b>\n"
        "/content — контент-план\n"
        "пост Идея, платформа, дата — добавить\n\n"
        "<b>Цели и достижения:</b>\n"
        "/goals — цели недели\n"
        "/achievements — все достижения\n"
        "/challenge — челлендж дня\n\n"
        "<b>Помодоро:</b>\n"
        "/focus45 — 45 мин таймер\n\n"
        "Нажми /go чтобы начать 👇"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=get_main_menu())


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
        f"🚀 <b>Just See — план запущен!</b>\n\n"
        f"<b>{day['d']} — {day['theme']}</b>\n\n"
        + "\n".join(f"  {i+1}. {t}" for i, t in enumerate(day["tasks"]))
        + "\n\nОтмечай задачи 👇"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=build_tasks_keyboard(data))
    await update.message.reply_text("Меню всегда под рукой 👇", reply_markup=get_main_menu())


async def tasks_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    if not data["started"]:
        await update.message.reply_text("Сначала запусти план: /go")
        return
    day = get_today_tasks(data)
    if not day:
        await update.message.reply_text("🏆 Все 60 дней пройдены! Just See Legend.")
        return
    done_mask = get_done_mask(data)
    done_count = sum(1 for d in done_mask if d)
    total = len(day["tasks"])
    text = f"📋 <b>{day['d']} — {day['theme']}</b>\nВыполнено: {done_count}/{total}\n\nОтмечай:"
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=build_tasks_keyboard(data))


async def progress_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    xp = data.get("xp", 0)
    rank = get_rank(xp)
    next_thresh, next_rank = get_next_rank(xp)
    streak = data.get("streak", 0)
    day_num = data.get("current_day", 0) + 1
    total_done = data.get("total_tasks_done", 0)
    bar_f = int(day_num / 60 * 20)
    day_bar = "█" * bar_f + "░" * (20 - bar_f)
    next_line = f"\n🎯 До <b>{next_rank}</b>: {next_thresh - xp} XP" if next_thresh else "\n👑 Максимальный ранг!"
    eff = round(total_done / max(day_num * 3, 1) * 100)
    achs = data.get("achievements", [])
    text = (
        f"📊 <b>Прогресс Just See Production</b>\n\n"
        f"🏅 Ранг: <b>{rank}</b>\n"
        f"⚡ XP: <b>{xp}</b>{next_line}\n"
        f"🔥 Стрик: <b>{streak}</b> дней\n\n"
        f"📅 День: <b>{day_num}/60</b>\n"
        f"[{day_bar}]\n\n"
        f"✅ Задач: <b>{total_done}</b>\n"
        f"💎 Эффективность: <b>{eff}%</b>\n"
        f"🏆 Достижений: <b>{len(achs)}/{len(ACHIEVEMENTS)}</b>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def stats_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    lines = ["📈 <b>История дней</b>\n"]
    for i in range(data.get("current_day", 0)):
        mask = data["tasks_done"].get(str(i), [])
        done = sum(1 for d in mask if d)
        total = len(PLAN[i]["tasks"]) if i < len(PLAN) else 3
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
    mask = get_done_mask(data)
    undone = [t for i, t in enumerate(day["tasks"]) if i >= len(mask) or not mask[i]]
    data["extra_tasks"] = undone + data.get("extra_tasks", [])
    data["streak"] = 0
    data["current_day"] = min(data["current_day"] + 1, len(PLAN) - 1)
    save_data(data)
    await update.message.reply_text(
        f"⏭ День пропущен. {len(undone)} задач перенесено. Стрик сброшен.")


async def shoot_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    data["shoot_mode"] = True
    day = get_today_tasks(data)
    undone = []
    if day:
        mask = get_done_mask(data)
        undone = [t for i, t in enumerate(day["tasks"]) if i >= len(mask) or not mask[i]]
        data["extra_tasks"] = undone + data.get("extra_tasks", [])
    data["current_day"] = min(data["current_day"] + 1, len(PLAN) - 1)
    save_data(data)
    await update.message.reply_text(
        f"🎬 <b>Съёмочный день!</b>\n\nБот уходит в тишину. {len(undone)} задач перенесено на завтра.\nУдачной съёмки, босс! 🎥",
        parse_mode="HTML")


async def quiet_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    args = ctx.args
    hours = int(args[0]) if args else 2
    until = (datetime.now() + timedelta(hours=hours)).isoformat()
    data["quiet_until"] = until
    save_data(data)
    await update.message.reply_text(f"🔕 Тишина на {hours} ч. Не буду беспокоить.")


async def focus_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    text = " ".join(ctx.args) if ctx.args else ""
    if not text:
        await update.message.reply_text("Напиши: /focus Твоя главная цель на сегодня")
        return
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_focus = data.get("daily_focus", [])
    daily_focus = [f for f in daily_focus if f["date"] != today_str]
    daily_focus.append({"date": today_str, "focus": text})
    data["daily_focus"] = daily_focus
    save_data(data)
    await update.message.reply_text(f"🎯 Фокус дня записан:\n<b>{text}</b>", parse_mode="HTML")


async def win_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    text = " ".join(ctx.args) if ctx.args else ""
    if not text:
        await update.message.reply_text("Напиши: /win Твоя победа")
        return
    wins = data.get("wins", [])
    wins.append({"text": text, "date": datetime.now().strftime("%Y-%m-%d")})
    data["wins"] = wins
    new_achs = check_achievements(data)
    data["xp"] = data.get("xp", 0) + 50
    save_data(data)
    msg = f"🌟 <b>Победа записана!</b>\n\n<i>{text}</i>\n\n+50 XP"
    if new_achs:
        msg += "\n\n" + "\n".join(f"🏆 {a['name']}" for a in new_achs)
    await update.message.reply_text(msg, parse_mode="HTML")


async def wins_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    wins = data.get("wins", [])
    if not wins:
        await update.message.reply_text("Побед пока нет. Используй /win Текст чтобы записать.")
        return
    lines = ["🌟 <b>Дневник побед Just See</b>\n"]
    for w in wins[-20:]:
        lines.append(f"• {w['date']}: {w['text']}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def achievements_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    earned = data.get("achievements", [])
    lines = [f"🏆 <b>Достижения</b> ({len(earned)}/{len(ACHIEVEMENTS)})\n"]
    for ach in ACHIEVEMENTS:
        icon = "✅" if ach["id"] in earned else "🔒"
        lines.append(f"{icon} {ach['name']} — {ach['desc']}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def challenge_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    ch = data.get("daily_challenge")
    done = data.get("challenge_done", False)
    if not ch:
        ch = random.choice(DAILY_CHALLENGES)
        data["daily_challenge"] = ch
        save_data(data)
    status = "✅ Выполнен!" if done else "⏳ В процессе"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Выполнил!", callback_data="challenge_done")]])
    await update.message.reply_text(
        f"⚡ <b>Челлендж дня</b>\n\n{ch['text']}\n\n+{ch['xp']} XP | {status}",
        parse_mode="HTML", reply_markup=None if done else kb)


async def focus45_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    end = (datetime.now() + timedelta(minutes=45)).isoformat()
    data["pomodoro_active"] = True
    data["pomodoro_end"] = end
    save_data(data)
    await update.message.reply_text("⏱ <b>Помодоро запущен — 45 минут!</b>\n\nФокус. Телефон в сторону. Just See ждёт результата.", parse_mode="HTML")
    await asyncio.sleep(45 * 60)
    data = load_data()
    data["pomodoro_active"] = False
    data["xp"] = data.get("xp", 0) + 50
    save_data(data)
    await update.message.reply_text("✅ <b>45 минут прошло!</b>\n\n+50 XP. Отдохни 10 минут — и снова в бой.", parse_mode="HTML")


# ─── CRM ─────────────────────────────────────────────────────────────────────
async def crm_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    leads = data.get("leads", [])
    if not leads:
        await update.message.reply_text("CRM пуста. Добавь лида: лид Имя, канал, источник")
        return
    statuses = ["холодный","тёплый","переговоры","договор","в работе","закрыт"]
    lines = ["📋 <b>CRM — лиды Just See</b>\n"]
    for s in statuses:
        group = [l for l in leads if l.get("status") == s]
        if group:
            lines.append(f"\n<b>{s.upper()} ({len(group)})</b>")
            for l in group:
                last = ""
                if l.get("last_contact"):
                    days = (datetime.now() - datetime.fromisoformat(l["last_contact"])).days
                    last = f" | {days}д назад"
                lines.append(f"• {l['name']} [{l.get('channel','')}]{last}")
                if l.get("next_step"):
                    lines.append(f"  → {l['next_step']}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def funnel_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    await update.message.reply_text(funnel_summary(data), parse_mode="HTML")


async def finance_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    await update.message.reply_text(finance_summary(data), parse_mode="HTML")


async def projects_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    projects = data.get("projects", [])
    if not projects:
        await update.message.reply_text("Проектов нет. Добавь: проект Название, клиент, дедлайн")
        return
    stages = ["бриф","препродакшен","съёмка","монтаж","правки","сдача","оплачен"]
    lines = ["🎬 <b>Проекты Just See</b>\n"]
    for p in projects:
        stage = p.get("stage","?")
        dl = p.get("deadline","")
        days_left = ""
        if dl:
            try:
                d = datetime.fromisoformat(dl)
                diff = (d - datetime.now()).days
                days_left = f" | ⏰ {diff}д" if diff >= 0 else f" | 🚨 просрочен {-diff}д"
            except:
                pass
        lines.append(f"• <b>{p['name']}</b> ({p.get('client','')})\n  Этап: {stage}{days_left}\n  Бюджет: {p.get('budget',0):,} ₽")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def content_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    content = data.get("content", [])
    if not content:
        await update.message.reply_text("Контент-план пуст. Добавь: пост Идея, платформа, дата")
        return
    statuses = ["идея","черновик","готов к публикации","опубликован"]
    lines = ["📱 <b>Контент-план Just See</b>\n"]
    for s in statuses:
        group = [c for c in content if c.get("status") == s]
        if group:
            lines.append(f"\n<b>{s.upper()}</b>")
            for c in group:
                lines.append(f"• {c['idea']} | {c.get('platform','')} | {c.get('date','')}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def goals_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    goals = data.get("weekly_goals", [])
    goals_done = data.get("weekly_goals_done", [])
    if not goals:
        await update.message.reply_text("Целей на неделю нет. Напиши их — бот сохранит и будет отслеживать.")
        return
    lines = ["🎯 <b>Цели недели</b>\n"]
    keyboard = []
    for i, g in enumerate(goals):
        done = g in goals_done
        icon = "✅" if done else "⬜"
        lines.append(f"{icon} {g}")
        if not done:
            keyboard.append([InlineKeyboardButton(f"✅ {g[:40]}", callback_data=f"goal_done_{i}")])
    msg = "\n".join(lines)
    kb = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=kb)



async def menu_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 <b>Just See — главное меню</b>",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )


async def learn_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await send_learn_card(ctx.application, update.effective_chat.id)


async def reflect_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await send_reflection(ctx.application, update.effective_chat.id)



# ─── ТЕКСТОВЫЕ БЫСТРЫЕ КОМАНДЫ ───────────────────────────────────────────────
async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    data = load_data()
    low = text.lower()

    # ЛИД
    if low.startswith("лид "):
        parts = text[4:].split(",")
        name = parts[0].strip() if parts else "?"
        channel = parts[1].strip() if len(parts) > 1 else ""
        source = parts[2].strip() if len(parts) > 2 else "холодный"
        lead = {
            "name": name, "channel": channel, "source": source,
            "status": "холодный", "budget": 0,
            "last_contact": datetime.now().isoformat(),
            "next_step": "", "deadline": ""
        }
        data.setdefault("leads", []).append(lead)
        new_achs = check_achievements(data)
        data["xp"] = data.get("xp", 0) + 30
        save_data(data)
        msg = f"✅ Лид добавлен: <b>{name}</b> [{channel}]\n+30 XP"
        if new_achs:
            msg += "\n" + "\n".join(f"🏆 {a['name']}" for a in new_achs)
        await update.message.reply_text(msg, parse_mode="HTML")

    # СДЕЛКА
    elif low.startswith("сделка "):
        parts = text[7:].split(",")
        name = parts[0].strip() if parts else "?"
        amount = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip().isdigit() else 0
        cost = int(parts[2].strip()) if len(parts) > 2 and parts[2].strip().isdigit() else 0
        dtype = parts[3].strip() if len(parts) > 3 else "клип"
        deal = {
            "name": name, "amount": amount, "cost": cost,
            "type": dtype, "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "оплачен"
        }
        data.setdefault("deals", []).append(deal)
        new_achs = check_achievements(data)
        profit = amount - cost
        data["xp"] = data.get("xp", 0) + 500
        save_data(data)
        to_goal = max(0, GOAL_AMOUNT - sum(d.get("amount",0) for d in data["deals"] if d.get("status")=="оплачен"))
        msg = (f"💰 <b>Сделка записана!</b>\n\n"
               f"Клиент: {name}\nОборот: {amount:,} ₽\nРасходы: {cost:,} ₽\nПрибыль: {profit:,} ₽\n"
               f"Тип: {dtype}\n\n+500 XP 🔥\nДо цели осталось: {to_goal:,} ₽")
        if new_achs:
            msg += "\n\n" + "\n".join(f"🏆 {a['name']}" for a in new_achs)
        await update.message.reply_text(msg, parse_mode="HTML")

    # ПРОЕКТ
    elif low.startswith("проект "):
        parts = text[7:].split(",")
        name = parts[0].strip()
        client = parts[1].strip() if len(parts) > 1 else ""
        deadline = parts[2].strip() if len(parts) > 2 else ""
        budget = int(parts[3].strip()) if len(parts) > 3 and parts[3].strip().isdigit() else 0
        project = {
            "name": name, "client": client, "deadline": deadline,
            "budget": budget, "stage": "бриф", "paid": False
        }
        data.setdefault("projects", []).append(project)
        save_data(data)
        await update.message.reply_text(
            f"🎬 <b>Проект добавлен!</b>\n\n{name} | {client}\nДедлайн: {deadline}\nБюджет: {budget:,} ₽\nЭтап: бриф",
            parse_mode="HTML")

    # ПОСТ
    elif low.startswith("пост "):
        parts = text[5:].split(",")
        idea = parts[0].strip()
        platform = parts[1].strip() if len(parts) > 1 else "Instagram"
        date = parts[2].strip() if len(parts) > 2 else datetime.now().strftime("%Y-%m-%d")
        content_item = {"idea": idea, "platform": platform, "date": date, "status": "идея"}
        data.setdefault("content", []).append(content_item)
        save_data(data)
        await update.message.reply_text(
            f"📱 <b>Пост добавлен!</b>\n\n{idea}\n{platform} | {date}\nСтатус: идея",
            parse_mode="HTML")

    # ПОБЕДА
    elif low.startswith("победа "):
        win_text = text[7:].strip()
        wins = data.get("wins", [])
        wins.append({"text": win_text, "date": datetime.now().strftime("%Y-%m-%d")})
        data["wins"] = wins
        data["xp"] = data.get("xp", 0) + 50
        new_achs = check_achievements(data)
        save_data(data)
        msg = f"🌟 <b>Победа!</b>\n\n{win_text}\n+50 XP"
        if new_achs:
            msg += "\n\n" + "\n".join(f"🏆 {a['name']}" for a in new_achs)
        await update.message.reply_text(msg, parse_mode="HTML")

    # ЦЕЛИ НЕДЕЛИ (свободный текст после запроса)
    elif data.get("awaiting_goals"):
        goals = [g.strip() for g in text.split("\n") if g.strip()]
        data["weekly_goals"] = goals
        data["weekly_goals_done"] = []
        data["awaiting_goals"] = False
        save_data(data)
        await update.message.reply_text(
            f"🎯 Цели на неделю записаны ({len(goals)} шт.):\n" + "\n".join(f"• {g}" for g in goals),
            parse_mode="HTML")

    # РЕФЛЕКСИЯ — обрабатываем ответы по одному
    elif data.get("reflection_q_idx") is not None and data.get("reflection_pending") is not None:
        q_idx = data.get("reflection_q_idx", 0)
        answers = data.get("reflection_answers", [])
        answers.append({"q": REFLECTION_QUESTIONS[q_idx], "a": text,
                        "date": datetime.now().strftime("%Y-%m-%d")})
        data["reflection_answers"] = answers
        q_idx += 1
        data["reflection_q_idx"] = q_idx
        if q_idx < len(REFLECTION_QUESTIONS):
            save_data(data)
            await update.message.reply_text(
                f"❓ <b>Вопрос {q_idx+1} из 5:</b>\n\n{REFLECTION_QUESTIONS[q_idx]}",
                parse_mode="HTML")
        else:
            # Сохраняем в историю рефлексий
            reflections = data.get("reflections", [])
            reflections.append({
                "week": datetime.now().strftime("%Y-W%W"),
                "answers": answers
            })
            data["reflections"] = reflections
            data["reflection_q_idx"] = None
            data["reflection_pending"] = None
            data["reflection_answers"] = []
            data["xp"] = data.get("xp", 0) + 200
            save_data(data)
            await update.message.reply_text(
                f"✅ <b>Рефлексия завершена!</b>\n\n+200 XP 🧠\n\nОтветы сохранены. Перечитай их в следующее воскресенье — увидишь прогресс.\n\n/reflect_history — история прошлых рефлексий",
                parse_mode="HTML")

    # КНОПКИ МЕНЮ
    elif text == "📋 Задачи":
        await tasks_command(update, ctx)
    elif text == "📊 Прогресс":
        await progress_command(update, ctx)
    elif text == "💰 Финансы":
        await finance_command(update, ctx)
    elif text == "👥 CRM":
        await crm_command(update, ctx)
    elif text == "🎬 Проекты":
        await projects_command(update, ctx)
    elif text == "📱 Контент":
        await content_command(update, ctx)
    elif text == "🏆 Достижения":
        await achievements_command(update, ctx)
    elif text == "🎯 Цели":
        await goals_command(update, ctx)
    elif text == "📚 Учиться":
        await learn_command(update, ctx)
    elif text == "🌟 Победы":
        await wins_command(update, ctx)
    elif text == "⚡ Челлендж":
        await challenge_command(update, ctx)
    elif text == "🪞 Рефлексия":
        await reflect_command(update, ctx)



# ─── CALLBACK КНОПКИ ─────────────────────────────────────────────────────────
async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = load_data()

    # Энергия
    if query.data.startswith("energy_"):
        energy = int(query.data.split("_")[1])
        today_str = datetime.now().strftime("%Y-%m-%d")
        log = data.get("energy_log", [])
        log = [e for e in log if e["date"] != today_str]
        log.append({"date": today_str, "energy": energy})
        data["energy_log"] = log
        save_data(data)
        emoji = "😴" if energy <= 3 else "😐" if energy <= 6 else "💪" if energy <= 8 else "🔥"
        await query.edit_message_text(f"⚡ Энергия дня: <b>{energy}/10</b> {emoji}\nЗафиксировано!", parse_mode="HTML")

    # Задача
    elif query.data.startswith("task_"):
        idx = int(query.data.split("_")[1])
        key = str(data["current_day"])
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
            if all_done:
                data["streak"] = data.get("streak", 0) + 1
                bonus = data["streak"] * STREAK_BONUS
                data["xp"] += bonus
                xp_gain += bonus
            feedback = f"✅ +{xp_gain} XP | {get_rank(data['xp'])}"
        else:
            data["xp"] = max(0, data.get("xp", 0) - XP_PER_TASK)
            data["total_tasks_done"] = max(0, data.get("total_tasks_done", 0) - 1)
            feedback = f"↩️ Отменено | XP: {data['xp']}"

        remaining = [day["tasks"][i] for i in range(total) if i >= len(mask) or not mask[i]]
        rem_line = ""
        if remaining and not all_done:
            rem_line = "\n\n📌 <b>Осталось:</b>\n" + "\n".join(f"• {t}" for t in remaining)

        new_achs = check_achievements(data)
        save_data(data)

        header = f"📋 <b>{day['d']} — {day['theme']}</b>\n{feedback}\nВыполнено: {done_count}/{total}{rem_line}"
        try:
            await query.edit_message_text(header, parse_mode="HTML", reply_markup=build_tasks_keyboard(data))
        except Exception:
            pass

        # Все сделаны
        if all_done and mask[idx]:
            deals = data.get("deals", [])
            revenue = sum(d.get("amount",0) for d in deals if d.get("status")=="оплачен")
            profit = revenue - sum(d.get("cost",0) for d in deals if d.get("status")=="оплачен")
            to_goal = max(0, GOAL_AMOUNT - revenue)
            goal_pct = min(100, int(revenue/GOAL_AMOUNT*100))
            bar = "█"*int(goal_pct/10) + "░"*(10-int(goal_pct/10))

            celebration = random.choice(ALL_DONE_MESSAGES)
            stats = (
                f"\n\n📊 <b>Статистика к цели:</b>\n"
                f"🎯 Цель: <b>1 000 000 ₽</b>\n"
                f"💰 Оборот: <b>{revenue:,} ₽</b>\n"
                f"💎 Прибыль: <b>{profit:,} ₽</b>\n"
                f"[{bar}] {goal_pct}%\n"
                f"Осталось: <b>{to_goal:,} ₽</b>\n"
                f"✅ Задач закрыто: <b>{data['total_tasks_done']}</b>\n"
                f"🔥 Стрик: <b>{data['streak']} дней</b>"
            )
            await query.message.reply_text(celebration + stats, parse_mode="HTML")

            for ach in new_achs:
                await query.message.reply_text(
                    f"🏆 <b>ДОСТИЖЕНИЕ!</b>\n{ach['name']}\n<i>{ach['desc']}</i>",
                    parse_mode="HTML")

    # Прогресс
    elif query.data == "progress":
        xp = data.get("xp", 0)
        streak = data.get("streak", 0)
        rank = get_rank(xp)
        next_thresh, next_rank = get_next_rank(xp)
        next_line = f"До {next_rank}: {next_thresh-xp} XP" if next_thresh else "Макс. ранг!"
        await query.answer(f"{rank} | XP: {xp} | 🔥{streak} дней\n{next_line}", show_alert=True)

    # Финансы быстро
    elif query.data == "finance_quick":
        deals = data.get("deals", [])
        revenue = sum(d.get("amount",0) for d in deals if d.get("status")=="оплачен")
        to_goal = max(0, GOAL_AMOUNT - revenue)
        await query.answer(f"Оборот: {revenue:,} ₽\nДо цели: {to_goal:,} ₽", show_alert=True)

    # Челлендж выполнен
    elif query.data == "challenge_done":
        ch = data.get("daily_challenge")
        if ch and not data.get("challenge_done"):
            data["challenge_done"] = True
            data["xp"] = data.get("xp", 0) + ch["xp"]
            save_data(data)
            await query.edit_message_text(
                f"⚡ <b>Челлендж выполнен!</b>\n\n{ch['text']}\n\n+{ch['xp']} XP 🔥",
                parse_mode="HTML")

    # Цель недели выполнена
    elif query.data.startswith("goal_done_"):
        idx = int(query.data.split("_")[-1])
        goals = data.get("weekly_goals", [])
        goals_done = data.get("weekly_goals_done", [])
        if idx < len(goals) and goals[idx] not in goals_done:
            goals_done.append(goals[idx])
            data["weekly_goals_done"] = goals_done
            data["xp"] = data.get("xp", 0) + 200
            save_data(data)
            await query.answer(f"✅ Цель выполнена! +200 XP", show_alert=True)

    # Карточка обучения
    elif query.data == "learn_apply":
        data["xp"] = data.get("xp", 0) + 50
        save_data(data)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.answer("✅ +50 XP! Применяй и результат придёт.", show_alert=True)

    elif query.data == "learn_next":
        card = random.choice(LEARNING_CARDS)
        text = (
            f"📚 <b>{card['topic']} — {card['title']}</b>\n\n"
            f"{card['text']}\n\n"
            f"<i>Применить сегодня?</i>"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Применю сегодня +50 XP", callback_data="learn_apply"),
            InlineKeyboardButton("📖 Ещё карточку", callback_data="learn_next"),
        ]])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)



async def reflect_history_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    reflections = data.get("reflections", [])
    if not reflections:
        await update.message.reply_text("Рефлексий пока нет. Первая — в воскресенье вечером, или /reflect прямо сейчас.")
        return
    last = reflections[-1]
    lines = [f"🪞 <b>Рефлексия {last['week']}</b>\n"]
    for i, ans in enumerate(last.get("answers", [])):
        lines.append(f"<b>Q{i+1}:</b> {ans['q']}")
        lines.append(f"<b>A:</b> {ans['a']}\n")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


# ─── MAIN ────────────────────────────────────────────────────────────────────
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
    app.add_handler(CommandHandler("shoot", shoot_command))
    app.add_handler(CommandHandler("quiet", quiet_command))
    app.add_handler(CommandHandler("focus", focus_command))
    app.add_handler(CommandHandler("focus45", focus45_command))
    app.add_handler(CommandHandler("win", win_command))
    app.add_handler(CommandHandler("wins", wins_command))
    app.add_handler(CommandHandler("achievements", achievements_command))
    app.add_handler(CommandHandler("challenge", challenge_command))
    app.add_handler(CommandHandler("crm", crm_command))
    app.add_handler(CommandHandler("funnel", funnel_command))
    app.add_handler(CommandHandler("finance", finance_command))
    app.add_handler(CommandHandler("projects", projects_command))
    app.add_handler(CommandHandler("content", content_command))
    app.add_handler(CommandHandler("goals", goals_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("learn", learn_command))
    app.add_handler(CommandHandler("reflect", reflect_command))
    app.add_handler(CommandHandler("reflect_history", reflect_history_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(send_morning_briefing, "cron", hour=9, minute=0, args=[app, OWNER_ID])
    scheduler.add_job(send_midday_check, "cron", hour=13, minute=0, args=[app, OWNER_ID])
    scheduler.add_job(send_evening_report, "cron", hour=21, minute=0, args=[app, OWNER_ID])
    scheduler.add_job(send_hourly_ping, "cron", hour="10-20", minute=0, args=[app, OWNER_ID])
    scheduler.add_job(send_weekly_report, "cron", day_of_week="sun", hour=20, minute=0, args=[app, OWNER_ID])
    scheduler.add_job(send_finance_weekly, "cron", day_of_week="sun", hour=20, minute=30, args=[app, OWNER_ID])
    scheduler.add_job(send_reflection, "cron", day_of_week="sun", hour=21, minute=0, args=[app, OWNER_ID])
    scheduler.start()

    print("Just See Bot запущен 🚀")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
