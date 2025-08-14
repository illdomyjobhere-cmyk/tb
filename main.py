import logging
import os
import time
import json
from pathlib import Path
import warnings
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
from telegram.warnings import PTBUserWarning

# Импорт токена из конфигурационного файла
from config import TOKEN

# Подавляем специфические предупреждения PTB
warnings.filterwarnings("ignore", category=PTBUserWarning)

# Состояния регистрации
GENDER, COUNTRY, AGE = range(3)

# Глобальные переменные
active_searches = {}
active_chats = {}
users = {}

# Клавиатуры
main_keyboard = ReplyKeyboardMarkup(
    [['Найти девушку', 'Рандом', 'Найти парня'],
     ['VIP статус', 'Комнаты', 'Профиль']],
    resize_keyboard=True
)

COUNTRIES = [
    "Россия", "Украина", "Беларусь", "Казахстан",
    "Узбекистан", "Страны ЕС", "США", "Другая"
]

AGE_GROUPS = [
    "до 14 лет", "От 15 до 17 лет", "от 18 до 21 года",
    "от 22 до 25 лет", "от 26 до 35", "от 36 лет"
]

def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"bot_{time.strftime('%Y%m%d_%H%M%S')}.log"
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Форматтер для файла
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Форматтер для консоли (без INFO:root)
    console_formatter = logging.Formatter('%(message)s')
    
    # Файловый обработчик
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    
    # Добавляем только наши сообщения в консоль
    class ConsoleFilter(logging.Filter):
        def filter(self, record):
            return record.name == "root"
    
    console_handler.addFilter(ConsoleFilter())
    
    # Убираем лишние логи библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def load_users():
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logging.error(f"Ошибка загрузки users.json: {e}")
        return {}

def save_users(users_data):
    try:
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Ошибка сохранения users.json: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    context.user_data.pop('in_registration', None)
    
    if user_id not in users:
        context.user_data['in_registration'] = True
        keyboard = [
            [InlineKeyboardButton("Я - парень", callback_data='male'),
             InlineKeyboardButton("Я - девушка", callback_data='female')]
        ]
        await update.message.reply_text(
            "👋 Добро пожаловать! Давайте зарегистрируемся.\nШаг 1: Ваш пол",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return GENDER
    
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
        await update.message.reply_text(
            "Главное меню:",
            reply_markup=main_keyboard
        )
    return ConversationHandler.END

async def registration_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    users[user_id] = {'gender': query.data}
    save_users(users)
    
    country_buttons = [InlineKeyboardButton(c, callback_data=c) for c in COUNTRIES]
    keyboard = [country_buttons[i:i+2] for i in range(0, len(country_buttons), 2)]
    
    await query.edit_message_text("Вы выбрали пол. Шаг 2: Ваша страна")
    await query.message.reply_text(
        "Выберите страну:",
        reply_markup=InlineKeyboardMarkup(keyboard))
    return COUNTRY

async def registration_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    users[user_id]['country'] = query.data
    save_users(users)
    
    keyboard = [[InlineKeyboardButton(age, callback_data=age)] for age in AGE_GROUPS]
    
    await query.edit_message_text("Вы выбрали страну. Шаг 3: Ваш возраст")
    await query.message.reply_text(
        "Выберите возрастную категорию:",
        reply_markup=InlineKeyboardMarkup(keyboard))
    return AGE

async def registration_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    users[user_id]['age'] = query.data
    save_users(users)
    context.user_data.pop('in_registration', None)
    
    await query.edit_message_text("✅ Регистрация завершена!")
    await query.message.reply_text(
        "Теперь вы можете начать поиск собеседника:",
        reply_markup=main_keyboard)
    return ConversationHandler.END

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    
    if user_id not in users:
        await update.message.reply_text(
            "❌ Вы не зарегистрированы! Введите /start",
            reply_markup=main_keyboard
        )
        return
    
    context.user_data.pop('in_registration', None)
    
    search_gender = None
    if update.message.text == 'Найти девушку':
        search_gender = 'female'
    elif update.message.text == 'Найти парня':
        search_gender = 'male'
    
    active_searches[user_id] = {'gender': search_gender}
    
    await update.message.reply_text(
        "🔍 Ищем собеседника...\n"
        "🛑 Чтобы остановить поиск, используйте /stop",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await find_partner(user_id, search_gender, context)

async def find_partner(user_id: str, search_gender: str, context: ContextTypes.DEFAULT_TYPE):
    for partner_id, partner_data in active_searches.items():
        if partner_id == user_id:
            continue
            
        compatible = True
        user_data = users[user_id]
        partner_user_data = users[partner_id]
        
        if search_gender and partner_user_data['gender'] != search_gender:
            compatible = False
            
        if partner_data['gender'] and user_data['gender'] != partner_data['gender']:
            compatible = False
            
        if compatible:
            del active_searches[user_id]
            del active_searches[partner_id]
            
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id
            
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
            return
    
    if user_id in active_searches:
        context.job_queue.run_once(
            lambda ctx: find_partner(user_id, search_gender, ctx[0]),
            5,
            context=context
        )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    
    if user_id in active_searches:
        del active_searches[user_id]
        await update.message.reply_text(
            "🛑 Поиск остановлен",
            reply_markup=main_keyboard
        )
    elif user_id in active_chats:
        partner_id = active_chats[user_id]
        del active_chats[user_id]
        
        if partner_id in active_chats:
            del active_chats[partner_id]
            await context.bot.send_message(
                partner_id,
                "❌ Собеседник завершил диалог\n\n"
                "🔍 Чтобы начать новый, используйте /start",
                reply_markup=main_keyboard
            )
        
        await update.message.reply_text(
            "🛑 Диалог завершен\n\n"
            "🔍 Чтобы начать новый, используйте /start",
            reply_markup=main_keyboard
        )
    else:
        await update.message.reply_text(
            "ℹ️ Вы не в диалоге и не в поиске.\n"
            "🔍 Чтобы начать поиск, используйте /start",
            reply_markup=main_keyboard
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(
            partner_id,
            update.message.text
        )
    else:
        await update.message.reply_text(
            "ℹ️ Вы не в диалоге\n"
            "🔍 Чтобы начать поиск, используйте /start",
            reply_markup=main_keyboard
        )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        message = update.message
        
        try:
            if message.photo:
                await context.bot.send_photo(
                    chat_id=partner_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption
                )
            elif message.video:
                await context.bot.send_video(
                    chat_id=partner_id,
                    video=message.video.file_id,
                    caption=message.caption
                )
            elif message.document:
                await context.bot.send_document(
                    chat_id=partner_id,
                    document=message.document.file_id,
                    caption=message.caption
                )
            elif message.audio:
                await context.bot.send_audio(
                    chat_id=partner_id,
                    audio=message.audio.file_id,
                    caption=message.caption
                )
            elif message.voice:
                await context.bot.send_voice(
                    chat_id=partner_id,
                    voice=message.voice.file_id
                )
        except Exception as e:
            logging.error(f"Ошибка отправки медиа: {e}")
            await update.message.reply_text("❌ Не удалось отправить медиа")
    else:
        await update.message.reply_text(
            "ℹ️ Вы не в диалоге\n"
            "🔍 Чтобы начать поиск, используйте /start",
            reply_markup=main_keyboard
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    context.user_data.pop('in_registration', None)
    
    if user_id in users and not all(k in users[user_id] for k in ['gender', 'country', 'age']):
        del users[user_id]
        save_users(users)
    
    await update.message.reply_text(
        "❌ Регистрация отменена",
        reply_markup=main_keyboard
    )
    return ConversationHandler.END

async def dummy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🚧 В разработке", reply_markup=main_keyboard)

def main() -> None:
    logger = setup_logging()
    logger.info("Бот запускается...")
    
    if not os.path.exists('users.json'):
        with open('users.json', 'w') as f:
            json.dump({}, f)
        logger.info("Создан новый файл users.json")
    
    global users
    users = load_users()
    logger.info(f"Загружено {len(users)} пользователей")
    
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [CallbackQueryHandler(registration_gender)],
            COUNTRY: [CallbackQueryHandler(registration_country)],
            AGE: [CallbackQueryHandler(registration_age)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    application.add_handler(conv_handler)

    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(MessageHandler(
        filters.Regex('^(Найти девушку|Рандом|Найти парня)$'),
        start_search))
    
    media_filter = (
        filters.PHOTO | filters.VIDEO | filters.Document.ALL | 
        filters.AUDIO | filters.VOICE
    )
    application.add_handler(MessageHandler(
        media_filter & filters.ChatType.PRIVATE,
        handle_media
    ))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_message
    ))

    commands = ['vip', 'link', 'ref', 'issue', 'search', 'top']
    for cmd in commands:
        application.add_handler(CommandHandler(cmd, dummy_command))

    logger.info("Бот начал работу")
    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
    finally:
        logger.info("Бот остановлен")

if __name__ == '__main__':
    main()