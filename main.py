import logging
import os
import time
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

# Создаем фильтр для разделения логов
class ConsoleFilter(logging.Filter):
    def filter(self, record):
        # Разрешаем только сообщения от корневого логгера (наши сообщения)
        return record.name == "root"

# Настройка логгирования
def setup_logging():
    # Создаем папку для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Создаем уникальное имя файла
    log_file = log_dir / f"bot_{time.strftime('%Y%m%d_%H%M%S')}.log"
    
    # Настройка основного логгера
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Форматтер для логов (подробный)
    detailed_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Форматтер для консоли (простой)
    simple_formatter = logging.Formatter('%(message)s')
    
    # Обработчик для файла (все сообщения)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Обработчик для консоли (только наши сообщения)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    
    # Добавляем фильтр, который пропускает только сообщения от корневого логгера
    console_handler.addFilter(ConsoleFilter())
    
    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Устанавливаем уровень логирования для библиотек
    logging.getLogger("httpx").setLevel(logging.DEBUG)
    logging.getLogger("httpcore").setLevel(logging.DEBUG)
    logging.getLogger("telegram").setLevel(logging.DEBUG)
    logging.getLogger("asyncio").setLevel(logging.DEBUG)
    
    return logger

# Глобальные переменные для хранения данных
users = {}
active_searches = {}
active_chats = {}
debug_mode = {}  # Словарь для хранения режима отладки по пользователям
message_mapping = {}  # Словарь для отслеживания соответствия сообщений между пользователями


async def send_any_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message: Update.message, debug_prefix: str = None, reply_to_message_id: int = None) -> int:
    """
    Универсальная функция для отправки любого типа сообщения
    """
    try:
        sent_message = None
        
        # Для видеосообщений (кружков) особая обработка
        if message.video_note:
            if debug_prefix:
                # Для видеосообщений в режиме отладки просто пересылаем как есть
                sent_message = await context.bot.send_video_note(
                    chat_id=chat_id, 
                    video_note=message.video_note.file_id,
                    reply_to_message_id=reply_to_message_id
                )
            else:
                sent_message = await context.bot.send_video_note(
                    chat_id=chat_id, 
                    video_note=message.video_note.file_id,
                    reply_to_message_id=reply_to_message_id
                )
            return sent_message.message_id if sent_message else None
        
        # Обработка остальных типов сообщений
        text = message.text
        caption = message.caption
        
        if debug_prefix:
            if text:
                text = f"{debug_prefix}: {text}"
            if caption:
                caption = f"{debug_prefix}: {caption}"
        
        if text:
            sent_message = await context.bot.send_message(
                chat_id=chat_id, 
                text=text,
                reply_to_message_id=reply_to_message_id
            )
        
        elif message.photo:
            sent_message = await context.bot.send_photo(
                chat_id=chat_id,
                photo=message.photo[-1].file_id,
                caption=caption,
                reply_to_message_id=reply_to_message_id
            )
        
        elif message.video:
            sent_message = await context.bot.send_video(
                chat_id=chat_id,
                video=message.video.file_id,
                caption=caption,
                reply_to_message_id=reply_to_message_id
            )
        
        elif message.document:
            sent_message = await context.bot.send_document(
                chat_id=chat_id,
                document=message.document.file_id,
                caption=caption,
                reply_to_message_id=reply_to_message_id
            )
        
        elif message.audio:
            sent_message = await context.bot.send_audio(
                chat_id=chat_id,
                audio=message.audio.file_id,
                caption=caption,
                reply_to_message_id=reply_to_message_id
            )
        
        elif message.voice:
            if debug_prefix:
                # Для голосовых в режиме отладки отправляем текст + голосовое
                text_msg = await context.bot.send_message(
                    chat_id=chat_id, 
                    text=f"{debug_prefix}: Голосовое сообщение",
                    reply_to_message_id=reply_to_message_id
                )
                sent_message = await context.bot.send_voice(
                    chat_id=chat_id, 
                    voice=message.voice.file_id
                )
                return text_msg.message_id  # Возвращаем ID текстового сообщения
            else:
                sent_message = await context.bot.send_voice(
                    chat_id=chat_id, 
                    voice=message.voice.file_id,
                    reply_to_message_id=reply_to_message_id
                )
        
        elif message.sticker:
            if debug_prefix:
                # Для стикеров в режиме отладки отправляем текст + стикер
                text_msg = await context.bot.send_message(
                    chat_id=chat_id, 
                    text=f"{debug_prefix}: Стикер",
                    reply_to_message_id=reply_to_message_id
                )
                sent_message = await context.bot.send_sticker(
                    chat_id=chat_id, 
                    sticker=message.sticker.file_id
                )
                return text_msg.message_id  # Возвращаем ID текстового сообщения
            else:
                sent_message = await context.bot.send_sticker(
                    chat_id=chat_id, 
                    sticker=message.sticker.file_id,
                    reply_to_message_id=reply_to_message_id
                )
        
        return sent_message.message_id if sent_message else None
    
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")
        return None


async def edit_any_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, new_message: Update.message, debug_prefix: str = None) -> bool:
    """
    Универсальная функция для редактирования сообщений
    :param context: контекст бота
    :param chat_id: ID чата
    :param message_id: ID сообщения для редактирования
    :param new_message: новое сообщение
    :param debug_prefix: префикс для режима отладки
    :return: True если успешно, False если ошибка
    """
    try:
        if new_message.text:
            # Редактирование текстового сообщения
            text = f"{debug_prefix}: {new_message.text}" if debug_prefix else new_message.text
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text
            )
            return True
        
        elif new_message.caption and (new_message.photo or new_message.video or new_message.document or new_message.audio):
            # Редактирование подписи медиафайла
            caption = f"{debug_prefix}: {new_message.caption}" if debug_prefix and new_message.caption else new_message.caption
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=caption
            )
            return True
            
        # Для других типов медиафайлов (фото, видео и т.д.) редактирование не поддерживается Telegram API
        # Нужно удалить старое сообщение и отправить новое
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        await send_any_message(context, chat_id, new_message, debug_prefix)
        return True
        
    except Exception as e:
        logging.error(f"Ошибка при редактировании сообщения: {e}")
        return False

# Состояния регистрации
GENDER, COUNTRY, AGE = range(3)

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

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Включение/выключение режима отладки"""
    user_id = update.message.from_user.id
    
    if user_id in debug_mode and debug_mode[user_id]:
        debug_mode[user_id] = False
        # Очищаем mapping сообщений
        if user_id in message_mapping:
            del message_mapping[user_id]
        await update.message.reply_text(
            "🔧 Режим отладки выключен\n"
            "Теперь бот работает в обычном режиме",
            reply_markup=main_keyboard
        )
    else:
        # Выходим из всех активных состояний
        if user_id in active_searches:
            del active_searches[user_id]
        if user_id in active_chats:
            partner_id = active_chats[user_id]
            if partner_id in active_chats:
                del active_chats[partner_id]
            del active_chats[user_id]
        
        # Очищаем mapping сообщений
        if user_id in message_mapping:
            del message_mapping[user_id]
        
        debug_mode[user_id] = True
        # Инициализируем mapping для режима отладки
        message_mapping[user_id] = {}
        
        await update.message.reply_text(
            "🔧 Режим отладки включен\n\n"
            "Все сообщения будут отправляться обратно вам.\n"
            "Поддерживаются ответы (reply) и редактирование сообщений.\n"
            "Для выхода из режима отладки используйте /debug",
            reply_markup=ReplyKeyboardRemove()
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    
    # Проверяем режим отладки
    if user_id in debug_mode and debug_mode[user_id]:
        await update.message.reply_text(
            "🔧 Вы в режиме отладки. Используйте /debug для выхода.\n"
            "Все сообщения будут отправляться обратно вам."
        )
        return ConversationHandler.END
    
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    
    # Проверяем режим отладки
    if user_id in debug_mode and debug_mode[user_id]:
        await update.message.reply_text(
            "🔧 Вы в режиме отладки. Используйте /debug для выхода.\n"
            "Все сообщения будут отправляться обратно вам."
        )
        return ConversationHandler.END
    
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
        reply_markup=InlineKeyboardMarkup(keyboard))
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
        reply_markup=InlineKeyboardMarkup(keyboard))
    return AGE

async def registration_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    users[user_id]['age'] = query.data
    
    await query.edit_message_text("✅ Регистрация завершена!")
    await query.message.reply_text(
        "Теперь вы можете начать поиск собеседника с помощью /start",
        reply_markup=main_keyboard)
    return ConversationHandler.END

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    
    # Проверяем режим отладки
    if user_id in debug_mode and debug_mode[user_id]:
        await update.message.reply_text(
            "🔧 Вы в режиме отладки. Используйте /debug для выхода.\n"
            "Все сообщения будут отправляться обратно вам."
        )
        return
    
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
        reply_markup=ReplyKeyboardRemove())
    
    # Поиск партнера
    await find_partner(user_id, search_gender, context)

async def find_partner(user_id: int, search_gender: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Проверяем режим отладки
    if user_id in debug_mode and debug_mode[user_id]:
        return
    
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
        
        # Инициализируем mapping сообщений для обоих пользователей
        message_mapping[user_id] = {}
        message_mapping[partner_id] = {}
        
        # Отправка уведомлений
        await context.bot.send_message(
            user_id,
            "💬 Собеседник найден! Начинайте общение\n\n"
            "🔄 /next - новый собеседник\n"
            "🛑 /stop - завершить диалог",
            reply_markup=ReplyKeyboardRemove())
        
        await context.bot.send_message(
            partner_id,
            "💬 Собеседник найден! Начинайте общение\n\n"
            "🔄 /next - новый собеседник\n"
            "🛑 /stop - завершить диалог",
            reply_markup=ReplyKeyboardRemove())

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    
    # Проверяем режим отладки
    if user_id in debug_mode and debug_mode[user_id]:
        await update.message.reply_text(
            "🔧 Вы в режиме отладки. Используйте /debug для выхода."
        )
        return
    
    if user_id in active_searches:
        # Остановка поиска
        del active_searches[user_id]
        await update.message.reply_text(
            "🛑 Поиск остановлен",
            reply_markup=main_keyboard)
    
    elif user_id in active_chats:
        # Завершение диалога
        partner_id = active_chats[user_id]
        
        if partner_id in active_chats:
            del active_chats[partner_id]
            await context.bot.send_message(
                partner_id,
                "❌ Собеседник завершил диалог\n\n"
                "🔍 Чтобы начать новый, используйте /start",
                reply_markup=main_keyboard)
        
        if user_id in active_chats:
            del active_chats[user_id]
        
        # Очищаем mapping сообщений
        if user_id in message_mapping:
            del message_mapping[user_id]
        if partner_id in message_mapping:
            del message_mapping[partner_id]
        
        await update.message.reply_text(
            "🛑 Диалог завершен\n\n"
            "🔍 Чтобы начать новый, используйте /start",
            reply_markup=main_keyboard)
    
    else:
        await update.message.reply_text(
            "🛑 Диалог остановлен\n\n"
            "🔍 Отправьте /start, чтобы начать поиск",
            reply_markup=main_keyboard)

async def next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    
    # Проверяем режим отладки
    if user_id in debug_mode and debug_mode[user_id]:
        await update.message.reply_text(
            "🔧 Вы в режиме отладки. Используйте /debug для выхода."
        )
        return
    
    if user_id in active_chats:
        # Завершение текущего диалога
        partner_id = active_chats[user_id]
        del active_chats[user_id]
        
        if partner_id in active_chats:
            del active_chats[partner_id]
            await context.bot.send_message(
                partner_id,
                "❌ Собеседник завершил диалог\n\n"
                "🔍 Чтобы начать новый, используйте /start",
                reply_markup=main_keyboard)
        
        # Очищаем mapping сообщений
        if user_id in message_mapping:
            del message_mapping[user_id]
        if partner_id in message_mapping:
            del message_mapping[partner_id]
        
        # Начало нового поиска
        await update.message.reply_text(
            "🔄 Ищем нового собеседника...\n"
            "🛑 Чтобы остановить поиск, используйте /stop",
            reply_markup=ReplyKeyboardRemove())
        active_searches[user_id] = {'gender': None}
        await find_partner(user_id, None, context)
    
    else:
        await update.message.reply_text(
            "ℹ️ Вы не в диалоге\n"
            "🔍 Чтобы начать поиск, используйте /start",
            reply_markup=main_keyboard)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    
    # Проверяем режим отладки
    if user_id in debug_mode and debug_mode[user_id]:
        # В режиме отладки отправляем сообщение обратно пользователю
        
        # Определяем ID сообщения для ответа (если это reply)
        reply_to_message_id = None
        if update.message.reply_to_message:
            # В режиме отладки отвечаем на ОРИГИНАЛЬНОЕ сообщение, а не на переотправленное
            reply_to_message_id = update.message.reply_to_message.message_id
        
        # Отправляем сообщение обратно пользователю
        sent_message_id = await send_any_message(context, user_id, update.message, "🔧 [DEBUG]", reply_to_message_id)
        
        # Сохраняем mapping сообщений для режима отладки (только для редактирования)
        if sent_message_id and user_id in message_mapping:
            message_mapping[user_id][update.message.message_id] = sent_message_id
        
        return

    
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        
        # Определяем ID сообщения для ответа (если это reply)
        reply_to_message_id = None
        if update.message.reply_to_message and user_id in message_mapping:
            # Ищем соответствующее сообщение у партнера
            original_message_id = update.message.reply_to_message.message_id
            if original_message_id in message_mapping[user_id]:
                reply_to_message_id = message_mapping[user_id][original_message_id]
        
        # Пересылаем сообщение собеседнику
        sent_message_id = await send_any_message(context, partner_id, update.message, None, reply_to_message_id)
        
        # Сохраняем mapping сообщений
        if sent_message_id and user_id in message_mapping:
            message_mapping[user_id][update.message.message_id] = sent_message_id
            if partner_id in message_mapping:
                message_mapping[partner_id][sent_message_id] = update.message.message_id
    
    else:
        await update.message.reply_text(
            "ℹ️ Вы не в диалоге\n"
            "🔍 Чтобы начать поиск, используйте /start",
            reply_markup=main_keyboard
        )

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка редактированных сообщений"""
    user_id = update.edited_message.from_user.id
    
    # Проверяем режим отладки
    if user_id in debug_mode and debug_mode[user_id]:
        # В режиме отладки редактируем сообщение у самого пользователя
        if user_id in message_mapping and update.edited_message.message_id in message_mapping[user_id]:
            debug_message_id = message_mapping[user_id][update.edited_message.message_id]
            
            # Пытаемся редактировать
            success = await edit_any_message(context, user_id, debug_message_id, update.edited_message, "🔧 [DEBUG]")
            
            if not success:
                # Если редактирование не удалось, переотправляем
                try:
                    await context.bot.delete_message(chat_id=user_id, message_id=debug_message_id)
                except:
                    pass
                new_message_id = await send_any_message(context, user_id, update.edited_message, "🔧 [DEBUG]")
                if new_message_id:
                    message_mapping[user_id][update.edited_message.message_id] = new_message_id
        else:
            # Сообщение не найдено в mapping - возможно, отправлено до включения режима
            # Создаем новый mapping
            if user_id not in message_mapping:
                message_mapping[user_id] = {}
            new_message_id = await send_any_message(context, user_id, update.edited_message, "🔧 [DEBUG]")
            if new_message_id:
                message_mapping[user_id][update.edited_message.message_id] = new_message_id
        return
    
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        
        # Ищем соответствующее сообщение у партнера
        if user_id in message_mapping and update.edited_message.message_id in message_mapping[user_id]:
            partner_message_id = message_mapping[user_id][update.edited_message.message_id]
            
            # Редактируем сообщение у партнера
            success = await edit_any_message(context, partner_id, partner_message_id, update.edited_message)
            
            if not success:
                # Если редактирование не удалось, отправляем новое сообщение
                await send_any_message(context, partner_id, update.edited_message)

async def handle_debug_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка редактированных сообщений в режиме отладки"""
    user_id = update.edited_message.from_user.id
    
    # Убедимся, что mapping существует
    if user_id not in message_mapping:
        message_mapping[user_id] = {}
    
    # Проверим, есть ли уже отправленная копия этого сообщения
    if update.edited_message.message_id in message_mapping[user_id]:
        # Сообщение уже было отправлено - редактируем его
        debug_message_id = message_mapping[user_id][update.edited_message.message_id]
        success = await edit_any_message(context, user_id, debug_message_id, update.edited_message, "🔧 [DEBUG]")
        
        if not success:
            # Если редактирование не удалось, удаляем старое и отправляем новое
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=debug_message_id)
            except:
                pass  # Игнорируем ошибки удаления
            new_message_id = await send_any_message(context, user_id, update.edited_message, "🔧 [DEBUG]")
            if new_message_id:
                message_mapping[user_id][update.edited_message.message_id] = new_message_id
    else:
        # Это новое сообщение (возможно, было отправлено до включения режима отладки)
        # Просто отправляем его как новое сообщение
        new_message_id = await send_any_message(context, user_id, update.edited_message, "🔧 [DEBUG]")
        if new_message_id:
            message_mapping[user_id][update.edited_message.message_id] = new_message_id

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Регистрация отменена")
    return ConversationHandler.END

async def dummy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🚧 В разработке")

def main() -> None:
    # Настройка логирования
    logger = setup_logging()
    logger.info("Бот запущен")
    
    # Создаем Application
    application = Application.builder().token(TOKEN).build()

    # Обработчик регистрации
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [CallbackQueryHandler(registration_gender)],
            COUNTRY: [CallbackQueryHandler(registration_country)],
            AGE: [CallbackQueryHandler(registration_age)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=True
    )
    application.add_handler(conv_handler)

    # Обработчики команд
    application.add_handler(CommandHandler("debug", debug))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("next", next))
    
    # Обработчики всех типов сообщений (кроме команд)
    application.add_handler(MessageHandler(
        filters.Regex('^(Найти девушку|Рандом|Найти парня)$'),
        start_search))
    
    # Обработчик для всех типов сообщений (текст, фото, видео, документы и т.д.)
    application.add_handler(MessageHandler(
        ~filters.COMMAND,
        handle_message))
    
    # Обработчик для редактированных сообщений
    application.add_handler(MessageHandler(
        filters.UpdateType.EDITED_MESSAGE & ~filters.COMMAND,
        handle_edited_message))

    # Заглушки для других команд
    commands = ['vip', 'link', 'ref', 'issue', 'search', 'top']
    for cmd in commands:
        application.add_handler(CommandHandler(cmd, dummy_command))

    # Запуск бота
    logger.info("Бот начал работу")
    try:
        application.run_polling()
    except Exception as e:
        logger.error(f"Бот остановлен из-за ошибки: {str(e)}")
        raise
    finally:
        logger.info("Бот остановлен")

if __name__ == '__main__':
    main()