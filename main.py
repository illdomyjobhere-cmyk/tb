import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния регистрации
GENDER, COUNTRY, AGE = range(3)

# Глобальные переменные для хранения данных
users = {}
active_searches = {}
active_chats = {}

# Настройки клавиатур
main_keyboard = ReplyKeyboardMarkup(
    [['Найти девушку', 'Рандом', 'Найти парня'],
     ['VIP статус', 'Комнаты', 'Профиль']],
    resize_keyboard=True
)

# Списки для регистрации
COUNTRIES = [
    "Россия", "Украина", "Беларусь", "Казахстан",
    "Узбекистан", "Страны ЕС", "США", "Другая"
]

AGE_GROUPS = [
    "до 14 лет", "От 15 до 17 лет", "от 18 до 21 года",
    "от 22 до 25 лет", "от 26 до 35", "от 36 лет"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id in users:
        if user_id in active_chats:
            await update.message.reply_text(
                "❌ Вы уже в диалоге! Завершите текущий диалог командой /stop",
                reply_markup=ReplyKeyboardRemove()
            )
        elif user_id in active_searches:
            await update.message.reply_text(
                "🔍 Вы уже в поиске! Остановите поиск командой /stop",
                reply_markup=main_keyboard
            )
        else:
            await start_search(update, context)
    else:
        # Начало процесса регистрации
        keyboard = [
            [InlineKeyboardButton("Я - парень", callback_data='male'),
             InlineKeyboardButton("Я - девушка", callback_data='female')]
        ]
        await update.message.reply_text(
            "👋 Добро пожаловать в анонимный чат!\n\n"
            "🛠️ Для использования бота требуется регистрация\n\n"
            "Шаг 1: Ваш пол",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return GENDER
    return ConversationHandler.END

async def registration_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users[user_id] = {'gender': query.data}
    
    # Клавиатура для выбора страны
    country_buttons = [InlineKeyboardButton(c, callback_data=c) for c in COUNTRIES]
    keyboard = [country_buttons[i:i+2] for i in range(0, len(country_buttons), 2)]
    
    await query.edit_message_text("Шаг 2: Ваша страна")
    await query.message.reply_text(
        "Выберите страну:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return COUNTRY

async def registration_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users[user_id]['country'] = query.data
    
    # Клавиатура для выбора возраста
    keyboard = [[InlineKeyboardButton(age, callback_data=age)] for age in AGE_GROUPS]
    
    await query.edit_message_text("Шаг 3: Ваш возраст")
    await query.message.reply_text(
        "Выберите возрастную категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return AGE

async def registration_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users[user_id]['age'] = query.data
    
    await query.edit_message_text("✅ Регистрация завершена!")
    await query.message.reply_text(
        "Теперь вы можете начать поиск собеседника с помощью /start",
        reply_markup=main_keyboard
    )
    return ConversationHandler.END

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in users:
        await update.message.reply_text("❌ Вы не зарегистрированы! Введите /start")
        return
    
    # Определение пола для поиска
    search_gender = None
    if update.message.text == 'Найти девушку':
        search_gender = 'female'
    elif update.message.text == 'Найти парня':
        search_gender = 'male'
    
    # Добавление в активный поиск
    active_searches[user_id] = {
        'gender': search_gender,
        'message_id': update.message.message_id
    }
    
    await update.message.reply_text(
        "🔍 Ищем собеседника...\n"
        "🛑 Чтобы остановить поиск, используйте /stop",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Поиск партнера (упрощенная реализация)
    await find_partner(user_id, search_gender, context)

async def find_partner(user_id: int, search_gender: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Поиск подходящего партнера
    partner_id = None
    for uid, data in active_searches.items():
        if uid == user_id:
            continue
        if not data['gender'] or data['gender'] == users[user_id]['gender']:
            partner_id = uid
            break
    
    if partner_id:
        # Создание чата
        del active_searches[user_id]
        del active_searches[partner_id]
        
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        
        # Отправка уведомлений
        await context.bot.send_message(
            user_id,
            "💬 Собеседник найден! Начинайте общение\n\n"
            "🔄 /next - новый собеседник\n"
            "🛑 /stop - завершить диалог",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await context.bot.send_message(
            partner_id,
            "💬 Собеседник найден! Начинайте общение\n\n"
            "🔄 /next - новый собеседник\n"
            "🛑 /stop - завершить диалог",
            reply_markup=ReplyKeyboardRemove()
        )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    
    if user_id in active_searches:
        # Остановка поиска
        del active_searches[user_id]
        await update.message.reply_text(
            "🛑 Поиск остановлен",
            reply_markup=main_keyboard
        )
    
    elif user_id in active_chats:
        # Завершение диалога
        partner_id = active_chats[user_id]
        
        del active_chats[user_id]
        del active_chats[partner_id]
        
        await update.message.reply_text(
            "🛑 Диалог завершен\n\n"
            "🔍 Чтобы начать новый, используйте /start",
            reply_markup=main_keyboard
        )
        
        await context.bot.send_message(
            partner_id,
            "❌ Собеседник завершил диалог\n\n"
            "🔍 Чтобы начать новый, используйте /start",
            reply_markup=main_keyboard
        )
    
    else:
        await update.message.reply_text(
            "ℹ️ Вы не в поиске и не в диалоге\n"
            "🔍 Чтобы начать поиск, используйте /start",
            reply_markup=main_keyboard
        )

async def next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    
    if user_id in active_chats:
        # Завершение текущего диалога
        partner_id = active_chats[user_id]
        del active_chats[user_id]
        del active_chats[partner_id]
        
        await context.bot.send_message(
            partner_id,
            "❌ Собеседник завершил диалог\n\n"
            "🔍 Чтобы начать новый, используйте /start",
            reply_markup=main_keyboard
        )
        
        # Начало нового поиска
        await update.message.reply_text(
            "🔄 Ищем нового собеседника...\n"
            "🛑 Чтобы остановить поиск, используйте /stop",
            reply_markup=ReplyKeyboardRemove()
        )
        active_searches[user_id] = {'gender': None}
        await find_partner(user_id, None, context)
    
    else:
        await update.message.reply_text(
            "ℹ️ Вы не в диалоге\n"
            "🔍 Чтобы начать поиск, используйте /start",
            reply_markup=main_keyboard
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(
            partner_id, 
            f"✉️ Сообщение от собеседника:\n\n{update.message.text}"
        )
    else:
        await update.message.reply_text(
            "ℹ️ Вы не в диалоге\n"
            "🔍 Чтобы начать поиск, используйте /start",
            reply_markup=main_keyboard
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Регистрация отменена")
    return ConversationHandler.END

async def dummy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🚧 В разработке")

def main() -> None:
    # Создаем Application
    application = Application.builder().token("1885649071:AAEAkbg16I0BICwkL90g8XfLFfOM0HfarQc").build()

    # Обработчик регистрации
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [CallbackQueryHandler(registration_gender)],
            COUNTRY: [CallbackQueryHandler(registration_country)],
            AGE: [CallbackQueryHandler(registration_age)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)

    # Обработчики команд
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("next", next))
    
    # Обработчики текстовых сообщений
    application.add_handler(MessageHandler(
        filters.Regex('^(Найти девушку|Рандом|Найти парня)$'),
        start_search
    ))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    # Заглушки для других команд
    commands = ['vip', 'link', 'ref', 'issue', 'search', 'top']
    for cmd in commands:
        application.add_handler(CommandHandler(cmd, dummy_command))

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()