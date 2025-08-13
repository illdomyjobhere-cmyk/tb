# ... (предыдущий код)

# Улучшенная функция загрузки пользователей
def load_users():
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r', encoding='utf-8') as f:
                users_data = json.load(f)
                logging.info(f"Загружено {len(users_data)} пользователей")
                return users_data
        return {}
    except Exception as e:
        logging.error(f"Ошибка загрузки users.json: {e}")
        return {}

# Улучшенная функция сохранения
def save_users(users_data):
    try:
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=4, ensure_ascii=False)
        logging.info(f"Сохранено {len(users_data)} пользователей")
    except Exception as e:
        logging.error(f"Критическая ошибка сохранения: {e}")

# Добавляем обработчики для текстовых сообщений в регистрации
async def registration_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Обрабатываем как текстовые сообщения, так и callback-и
    if update.message:
        text = update.message.text
        gender_map = {
            "Я - парень": "male",
            "Я - девушка": "female"
        }
        if text not in gender_map:
            await update.message.reply_text("Пожалуйста, используйте кнопки для выбора пола")
            return GENDER
        gender = gender_map[text]
        user_id = str(update.message.from_user.id)
    else:
        query = update.callback_query
        await query.answer()
        gender = query.data
        user_id = str(query.from_user.id)
        await query.edit_message_text(f"Вы выбрали: {'парень' if gender == 'male' else 'девушка'}")

    users[user_id] = {'gender': gender}
    save_users(users)
    
    # Клавиатура для выбора страны (теперь ReplyKeyboard)
    country_keyboard = [COUNTRIES[i:i+2] for i in range(0, len(COUNTRIES), 2)]
    await context.bot.send_message(
        user_id,
        "Шаг 2: Ваша страна\nВыберите из списка:",
        reply_markup=ReplyKeyboardMarkup(country_keyboard, resize_keyboard=True)
    return COUNTRY

# Аналогично улучшаем другие шаги регистрации...

# В функции start добавляем проверку состояния
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    
    # Проверяем, не в процессе ли регистрации
    if context.user_data.get('in_registration'):
        await update.message.reply_text("Завершите текущую регистрацию!")
        return ConversationHandler.END
        
    if user_id in users:
        # ... существующая логика ...
    else:
        context.user_data['in_registration'] = True
        # Используем ReplyKeyboard вместо Inline
        reply_keyboard = [["Я - парень", "Я - девушка"]]
        await update.message.reply_text(
            "👋 Добро пожаловать!\nШаг 1: Ваш пол",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, 
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        return GENDER

# Добавляем обработку отмены регистрации
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.message.from_user.id)
    if user_id in context.user_data:
        context.user_data.pop('in_registration', None)
    await update.message.reply_text("Регистрация отменена", reply_markup=main_keyboard)
    return ConversationHandler.END

# В main() улучшаем ConversationHandler
def main() -> None:
    # ... (предыдущий код)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GENDER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, registration_gender),
                CallbackQueryHandler(registration_gender)
            ],
            COUNTRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, registration_country),
                CallbackQueryHandler(registration_country)
            ],
            AGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, registration_age),
                CallbackQueryHandler(registration_age)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True  # Разрешаем перезапуск регистрации
    )
    
    # ... (остальной код)