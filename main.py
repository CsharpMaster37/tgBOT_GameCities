import telebot
import sqlite3
from telebot import types
import os

# Ваш токен для Telegram бота
bot = telebot.TeleBot('7081768866:AAHv7_VwjwlYR48KfgeanICd6z-8vp8ERys')

# Чтение правил игры из файла
with open('rules.txt', 'r', encoding='utf-8') as file_rules:
    _rules = file_rules.read()

# Список городов
with open('cities.txt', 'r', encoding='utf-8') as f:
    cities = [city.strip().capitalize() for city in f.read().splitlines()]

# Функции для работы с текстовыми файлами
def create_used_cities_file(user_id, cities_used):
    folder = 'games'
    if not os.path.exists(folder):
        os.makedirs(folder)
    with open(f'{folder}/{user_id}_used_cities.txt', 'w', encoding='utf-8') as file:
        for city in cities_used:
            file.write(city + '\n')

def read_used_cities_file(user_id):
    used_cities = []
    try:
        with open(f'games/{user_id}_used_cities.txt', 'r', encoding='utf-8') as file:
            used_cities = [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        pass
    return used_cities

def delete_used_cities_file(user_id):
    try:
        os.remove(f'games/{user_id}_used_cities.txt')
    except FileNotFoundError:
        pass

# region Обработка команд
@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect('gamecities.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_games (
        id INTEGER PRIMARY KEY, 
        name TEXT, 
        score INTEGER, 
        status BOOLEAN,
        last_city TEXT
    )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS leaderboard (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        name TEXT, 
        score INTEGER
    )
    ''')

    cur.execute('SELECT id FROM user_games WHERE id = ?', (message.chat.id,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO user_games (id, name, score, status, last_city) VALUES (?, ?, ?, ?, ?);",
                    (message.chat.id, message.chat.username, 0, False, None))

    conn.commit()
    cur.close()
    conn.close()

    _message = 'Привет! Это игра "Города". Используйте кнопки в меню для управления игрой.'
    bot.send_message(message.chat.id, _message)
    show_menu(message)

@bot.message_handler(commands=['game'])
def game(message):
    start_game(message)

def start_game(message):
    conn = sqlite3.connect('gamecities.db')
    cur = conn.cursor()

    cur.execute('UPDATE user_games SET status = ? WHERE id = ?', (True, message.chat.id))
    cur.execute('SELECT last_city, score FROM user_games WHERE id = ?', (message.chat.id,))
    last_city, score = cur.fetchone()

    used_cities = read_used_cities_file(message.chat.id)
    if not last_city:
        bot_city = "Москва"
        cur.execute('UPDATE user_games SET last_city = ? WHERE id = ?', (bot_city, message.chat.id))
        bot.send_message(message.chat.id, f'Мой город: {bot_city}. Теперь ваша очередь!')
        used_cities.append(bot_city)
        create_used_cities_file(message.chat.id, used_cities)
    else:
        bot.send_message(message.chat.id, f'Последний город был: {last_city}. Ваш счёт: {score}. Ваш ход!')

    conn.commit()
    cur.close()
    conn.close()

    show_game_controls(message)

# endregion

# region Обработка текста
@bot.message_handler(content_types=['text'])
def get_user_text(message):
    if message.text == 'Правила':
        bot.send_message(message.chat.id, _rules)
    elif message.text == 'Список пользователей':
        list_users(message)
    elif message.text == 'Таблица лидеров':
        show_leaderboard(message)
    elif message.text == 'Меню':
        show_menu(message)
    elif message.text == 'Сдаться':
        give_up(message)
    elif message.text == 'Назад':
        pause_game(message)
    elif message.text in ['Играть', 'Продолжить игру']:
        start_game(message)
    else:
        process_city(message)

def list_users(message):
    conn = sqlite3.connect('gamecities.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM user_games')
    games = cur.fetchall()
    info = ''
    for item in games:
        info += f'ID: {item[0]}, Имя: {item[1]}, Очки: {item[2]}, Статус игры: {"Активна" if item[3] else "Не активна"}, Последний город: {item[4]}\n'
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, info)

def show_leaderboard(message):
    conn = sqlite3.connect('gamecities.db')
    cur = conn.cursor()
    cur.execute('SELECT name, score FROM leaderboard ORDER BY score DESC')
    leaders = cur.fetchall()
    if leaders:
        leaderboard_text = '🏆 Таблица лидеров:\n'
        for i, leader in enumerate(leaders, start=1):
            leaderboard_text += f'{i}. {leader[0]} - {leader[1]} очков\n'
    else:
        leaderboard_text = 'Таблица лидеров пуста.'
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, leaderboard_text)

def show_menu(message):
    conn = sqlite3.connect('gamecities.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM user_games WHERE id = ?', (message.chat.id,))
    user_game = cur.fetchone()
    cur.close()
    conn.close()

    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_game = types.KeyboardButton('Играть' if not user_game[3] else 'Продолжить игру')
    button_rules = types.KeyboardButton('Правила')
    button_list = types.KeyboardButton('Список пользователей')
    button_leaderboard = types.KeyboardButton('Таблица лидеров')
    keyboard.add(button_game, button_rules, button_list, button_leaderboard)

    bot.send_message(message.chat.id, 'Меню:', reply_markup=keyboard)

def show_game_controls(message):
    keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    button_give_up = types.KeyboardButton('Сдаться')
    button_back = types.KeyboardButton('Назад')
    keyboard.add(button_give_up, button_back)
    bot.send_message(message.chat.id, 'Игра идет:', reply_markup=keyboard)

def process_city(message):
    user_city = message.text.strip().capitalize()

    used_cities = read_used_cities_file(message.chat.id)
    if user_city in used_cities:
        bot.send_message(message.chat.id, "Этот город уже был использован.")
        return

    if user_city not in cities:
        bot.send_message(message.chat.id, "Такого города нет.")
        return

    conn = sqlite3.connect('gamecities.db')
    cur = conn.cursor()
    cur.execute('SELECT last_city, score FROM user_games WHERE id = ?', (message.chat.id,))
    last_city, score = cur.fetchone()

    if last_city:
        last_letter = last_city[-1].lower()

        if last_letter in ['ь', 'ъ']:
            last_letter = last_city[-2].lower()

        if last_letter != user_city[0].lower():
            bot.send_message(message.chat.id, f'Ваш город должен начинаться на букву "{last_letter.upper()}". Попробуйте снова.')
            cur.close()
            conn.close()
            return

    score += 1
    cur.execute('UPDATE user_games SET score = ?, last_city = ? WHERE id = ?', (score, user_city, message.chat.id))
    used_cities.append(user_city)
    create_used_cities_file(message.chat.id, used_cities)

    bot_city = None
    for city in cities:
        bot_city_first_letter = city[0].lower()
        if bot_city_first_letter == user_city[-1].lower():
            if user_city[-1].lower() in ['ь', 'ъ']:
                bot_city_first_letter = city[1].lower()
            bot_city = city
            break

    if bot_city:
        used_cities.append(bot_city)
        create_used_cities_file(message.chat.id, used_cities)
        cur.execute('UPDATE user_games SET last_city = ? WHERE id = ?', (bot_city, message.chat.id))
        bot.send_message(message.chat.id, f'Мой город: {bot_city}. Ваш счёт: {score}. Ваш ход!')
    else:
        bot.send_message(message.chat.id, f'Я не знаю больше городов на эту букву. Вы победили! Ваш счёт: {score} очков.')
        record_leaderboard(message.chat.id, message.chat.username, score)
        cur.execute('UPDATE user_games SET status = ? WHERE id = ?', (False, message.chat.id))
        show_menu(message)

    conn.commit()
    cur.close()
    conn.close()


def record_leaderboard(user_id, username, score):
    conn = sqlite3.connect('gamecities.db')
    cur = conn.cursor()

    cur.execute('SELECT score FROM leaderboard WHERE name = ?', (username,))
    existing_score = cur.fetchone()

    if existing_score:
        if score > existing_score[0]:
            cur.execute('UPDATE leaderboard SET score = ? WHERE name = ?', (score, username))
    else:
        cur.execute('INSERT INTO leaderboard (name, score) VALUES (?, ?)', (username, score))

    conn.commit()
    cur.close()
    conn.close()

def give_up(message):
    conn = sqlite3.connect('gamecities.db')
    cur = conn.cursor()
    cur.execute('SELECT score FROM user_games WHERE id = ?', (message.chat.id,))
    score = cur.fetchone()[0]
    record_leaderboard(message.chat.id, message.chat.username, score)
    cur.execute('UPDATE user_games SET status = ?, score = ?, last_city = ? WHERE id = ?',
                (False, 0, None, message.chat.id))
    conn.commit()
    cur.close()
    conn.close()
    delete_used_cities_file(message.chat.id)
    bot.send_message(message.chat.id, 'Вы сдались.')
    show_menu(message)

def pause_game(message):
    conn = sqlite3.connect('gamecities.db')
    cur = conn.cursor()
    cur.execute('UPDATE user_games SET status = ? WHERE id = ?', (True, message.chat.id))
    conn.commit()
    cur.close()
    conn.close()
    bot.send_message(message.chat.id, 'Игра приостановлена. Возвращайтесь, когда будете готовы!')
    show_menu(message)

# endregion

bot.polling(none_stop=True)
