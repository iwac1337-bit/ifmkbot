import json
from datetime import date, datetime, timedelta

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задана переменная BOT_TOKEN")


# ============================================================
# ЗАГРУЗКА РАСПИСАНИЯ
# ============================================================

with open("schedule.json", "r", encoding="utf-8") as file:
    data = json.load(file)


META = data["meta"]
SCHEDULE = data["schedule"]

SEMESTER_START = datetime.strptime(
    META["semester_start"],
    "%Y-%m-%d"
).date()

TOTAL_WEEKS = META["total_weeks"]

GROUPS = list(META["groups"].keys())


# ============================================================
# ДНИ НЕДЕЛИ
# ============================================================

WEEKDAYS = {
    0: "понедельник",
    1: "вторник",
    2: "среда",
    3: "четверг",
    4: "пятница",
    5: "суббота",
    6: "воскресенье",
}

WEEKDAY_NAMES = {
    "понедельник": "Понедельник",
    "вторник": "Вторник",
    "среда": "Среда",
    "четверг": "Четверг",
    "пятница": "Пятница",
    "суббота": "Суббота",
    "воскресенье": "Воскресенье",
}


# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def groups_keyboard():
    """
    Кнопки выбора группы.
    """

    return ReplyKeyboardMarkup(
        [
            ["510-1", "510-2"],
            ["511-1", "511-2"],
        ],
        resize_keyboard=True
    )


def main_keyboard():
    """
    Главное меню после выбора группы.
    """

    return ReplyKeyboardMarkup(
        [
            ["📅 Сегодня", "📅 Завтра"],
            ["📚 Эта неделя"],
            ["📖 Расписание на неделю"],
            ["🔄 Сменить группу"],
        ],
        resize_keyboard=True
    )


# ============================================================
# ОПРЕДЕЛЕНИЕ УЧЕБНОЙ НЕДЕЛИ
# ============================================================

def get_semester_week(target_date: date) -> int:
    """
    Определяет номер недели семестра.

    semester_start = начало 1-й недели.

    Например:

    01.09 - 07.09 -> неделя 1
    08.09 - 14.09 -> неделя 2
    15.09 - 21.09 -> неделя 3

    и т.д.
    """

    days_from_start = (target_date - SEMESTER_START).days

    week = days_from_start // 7 + 1

    return week


# ============================================================
# ПРОВЕРКА: ЕСТЬ ЛИ РАСПИСАНИЕ НА ЭТУ НЕДЕЛЮ
# ============================================================

def get_lessons_for_date(group: str, target_date: date):
    """
    Возвращает пары конкретной группы
    на конкретную дату.

    Учитываются:
    - день недели;
    - номер учебной недели;
    - массив weeks из JSON.
    """

    semester_week = get_semester_week(target_date)

    weekday = WEEKDAYS[target_date.weekday()]

    result = []

    # Если такой группы нет
    if group not in SCHEDULE:
        return result

    group_schedule = SCHEDULE[group]

    # Если в этот день нет расписания
    if weekday not in group_schedule:
        return result

    day_schedule = group_schedule[weekday]

    # Проходим по времени
    for time, lessons in day_schedule.items():

        # lessons — это список занятий
        for lesson in lessons:

            lesson_weeks = lesson.get("weeks", [])

            # Проверяем, проводится ли занятие
            # на текущей учебной неделе
            if semester_week in lesson_weeks:

                result.append({
                    "time": time,
                    "text": lesson.get("text", "")
                })

    return result


# ============================================================
# ФОРМАТИРОВАНИЕ РАСПИСАНИЯ НА ДЕНЬ
# ============================================================

def format_day_schedule(
    group: str,
    target_date: date
) -> str:

    weekday = WEEKDAYS[target_date.weekday()]
    weekday_name = WEEKDAY_NAMES[weekday]

    semester_week = get_semester_week(target_date)

    lessons = get_lessons_for_date(
        group,
        target_date
    )

    result = []

    result.append(
        f"📅 {weekday_name}, "
        f"{target_date.strftime('%d.%m.%Y')}"
    )

    result.append(
        f"👥 Группа: {group}"
    )

    result.append(
        f"📚 Учебная неделя: {semester_week}"
    )

    result.append("")

    # До начала или после окончания семестра
    if semester_week < 1:
        result.append(
            "Семестр ещё не начался."
        )
        return "\n".join(result)

    if semester_week > TOTAL_WEEKS:
        result.append(
            "Расписание семестра на эту дату "
            "не предусмотрено."
        )
        return "\n".join(result)

    # Если пар нет
    if not lessons:
        result.append(
            "🎉 Пар сегодня нет."
        )

        return "\n".join(result)

    # Выводим пары
    for number, lesson in enumerate(
        lessons,
        start=1
    ):

        result.append(
            f"🕐 {lesson['time']}"
        )

        result.append(
            f"📖 {lesson['text']}"
        )

        result.append("")

    return "\n".join(result)


# ============================================================
# РАСПИСАНИЕ НА НЕДЕЛЮ
# ============================================================

def format_week_schedule(
    group: str,
    start_date: date
) -> str:

    semester_week = get_semester_week(
        start_date
    )

    result = []

    result.append(
        f"📚 Расписание группы {group}"
    )

    result.append(
        f"Учебная неделя: {semester_week}"
    )

    result.append("")

    # 7 дней
    for i in range(7):

        current_date = (
            start_date +
            timedelta(days=i)
        )

        weekday = WEEKDAYS[
            current_date.weekday()
        ]

        weekday_name = WEEKDAY_NAMES[
            weekday
        ]

        lessons = get_lessons_for_date(
            group,
            current_date
        )

        result.append(
            f"━━━━━━━━━━━━━━━━━━"
        )

        result.append(
            f"📅 {weekday_name} "
            f"{current_date.strftime('%d.%m')}"
        )

        if not lessons:

            result.append(
                "Нет пар."
            )

            continue

        for lesson in lessons:

            result.append(
                f"\n🕐 {lesson['time']}"
            )

            result.append(
                f"📖 {lesson['text']}"
            )

    return "\n".join(result)


# ============================================================
# /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Я бот с расписанием.\n"
        "Сначала выбери свою группу:",
        reply_markup=groups_keyboard()
    )


# ============================================================
# ВЫБОР ГРУППЫ
# ============================================================

async def select_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    group = update.message.text

    if group not in GROUPS:
        return

    # Запоминаем группу пользователя
    context.user_data["group"] = group

    group_name = META["groups"].get(
        group,
        group
    )

    await update.message.reply_text(
        f"✅ Группа выбрана!\n\n"
        f"Группа: {group}\n"
        f"{group_name}\n\n"
        f"Теперь выбери, что показать:",
        reply_markup=main_keyboard()
    )


# ============================================================
# СЕГОДНЯ
# ============================================================

async def show_today(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    group = context.user_data.get("group")

    if not group:
        await update.message.reply_text(
            "Сначала выбери группу.\n"
            "Используй /start"
        )
        return

    today = date.today()

    text = format_day_schedule(
        group,
        today
    )

    await update.message.reply_text(
        text
    )


# ============================================================
# ЗАВТРА
# ============================================================

async def show_tomorrow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    group = context.user_data.get("group")

    if not group:
        await update.message.reply_text(
            "Сначала выбери группу.\n"
            "Используй /start"
        )
        return

    tomorrow = (
        date.today() +
        timedelta(days=1)
    )

    text = format_day_schedule(
        group,
        tomorrow
    )

    await update.message.reply_text(
        text
    )


# ============================================================
# ЭТА НЕДЕЛЯ
# ============================================================

async def show_current_week(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    group = context.user_data.get("group")

    if not group:
        await update.message.reply_text(
            "Сначала выбери группу.\n"
            "Используй /start"
        )
        return

    today = date.today()

    # Понедельник текущей недели
    monday = (
        today -
        timedelta(days=today.weekday())
    )

    text = format_week_schedule(
        group,
        monday
    )

    await update.message.reply_text(
        text
    )


# ============================================================
# ПОЛНОЕ РАСПИСАНИЕ НА НЕДЕЛЮ
# ============================================================

async def show_week_schedule(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    group = context.user_data.get("group")

    if not group:
        await update.message.reply_text(
            "Сначала выбери группу.\n"
            "Используй /start"
        )
        return

    today = date.today()

    monday = (
        today -
        timedelta(days=today.weekday())
    )

    text = format_week_schedule(
        group,
        monday
    )

    await update.message.reply_text(
        text
    )


# ============================================================
# СМЕНИТЬ ГРУППУ
# ============================================================

async def change_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "Выбери новую группу:",
        reply_markup=groups_keyboard()
    )


# ============================================================
# ОБРАБОТКА КНОПОК
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text

    # -----------------------------------------
    # Если пользователь выбирает группу
    # -----------------------------------------

    if text in GROUPS:

        await select_group(
            update,
            context
        )

        return

    # -----------------------------------------
    # Сменить группу
    # -----------------------------------------

    if text == "🔄 Сменить группу":

        await change_group(
            update,
            context
        )

        return

    # -----------------------------------------
    # Сегодня
    # -----------------------------------------

    if text == "📅 Сегодня":

        await show_today(
            update,
            context
        )

        return

    # -----------------------------------------
    # Завтра
    # -----------------------------------------

    if text == "📅 Завтра":

        await show_tomorrow(
            update,
            context
        )

        return

    # -----------------------------------------
    # Эта неделя
    # -----------------------------------------

    if text == "📚 Эта неделя":

        await show_current_week(
            update,
            context
        )

        return

    # -----------------------------------------
    # Расписание на неделю
    # -----------------------------------------

    if text == "📖 Расписание на неделю":

        await show_week_schedule(
            update,
            context
        )

        return


# ============================================================
# ЗАПУСК
# ============================================================

def main():

    print("🚀 Бот запускается...")

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # Команда /start
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # Все обычные сообщения
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("✅ Бот запущен!")

    app.run_polling()


# ============================================================
# ТОЧКА ВХОДА
# ============================================================

if __name__ == "__main__":
    main()
