import os
from datetime import datetime

import telebot
from telebot import types

import sqlite3

from config import BOT_TOKEN, BASE_PATH, LAST_RUN_FILE, OWNER

bot = telebot.TeleBot(BOT_TOKEN)

printy = bot.send_message


@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    registration = types.KeyboardButton("Регистрация")
    already_reg = types.KeyboardButton("Я уже зарегистрирован")
    
    markup.add(registration, already_reg)
    printy(message.chat.id, f"Привет {message.from_user.first_name}!", reply_markup=markup)

def get_last_run_time():
    if os.path.exists(LAST_RUN_FILE):
        with open(LAST_RUN_FILE, 'r') as file:
            return float(file.read().strip())
    return None

def update_last_run_time():
    with open(LAST_RUN_FILE, 'w') as file:
        file.write(str(datetime.now().timestamp()))

def connect_to_db():
    try:
        con = sqlite3.connect(BASE_PATH)
        cur = con.cursor()
        return con, cur
    except BaseException as e:
        print(e)
        print("Ошибка подключения к БД")

def registration(message):
    def registrationId(message):
        printy(message.chat.id, "Введите Ваше имя и фамилию")
        
        con, cur = connect_to_db()
        try:
            cur.execute("INSERT INTO baseReg (user_id) VALUES (?)", (message.chat.id,))
            con.commit()
        except sqlite3.IntegrityError:
            printy(message.chat.id, "Вы уже зарегистрированы.")
        finally:
            con.close()

        bot.register_next_step_handler(message, registrationName)
    
    def registrationName(message):
        con, cur = connect_to_db()
        try:
            cur.execute("UPDATE baseReg SET name = ? WHERE user_id = ?", (message.text, message.chat.id))
            con.commit()
            printy(message.chat.id, f"Привет {message.from_user.first_name}!")
        except Exception as e:
            print("Ошибка заполнения БД (name)", e)
            printy(message.chat.id, "Произошла ошибка при обновлении данных.")
        finally:
            con.close()

        interface(message)
    
    registrationId(message)

def interface(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    information = types.KeyboardButton("Информация о боте")
    see = types.KeyboardButton("Посмотреть список")
    entry = types.KeyboardButton("Записаться на ближайшую сдачу")
    clear_my_entry = types.KeyboardButton("Удалить свою запись")
    markup.add(entry, see, information, clear_my_entry)
    printy(message.chat.id, "Возможности:", reply_markup=markup)

def clear_entries(message):
    con, cur = connect_to_db()
    try:
        cur.execute("DELETE FROM baseEntry")
        con.commit()
        printy(message.chat.id, "Все текущие записи были удалены.")
    except BaseException as e:
        print("Ошибка при удалении записей из БД", e)
        printy(message.chat.id, "Не удалось удалить записи.")
    finally:
        con.close()

def clear_entrie(message):
    con, cur = connect_to_db()
    try:
        cur.execute("DELETE FROM baseEntry WHERE user_id = ?", (message.chat.id,))
        con.commit()

        if cur.rowcount > 0:
            printy(message.chat.id, "Ваша запись была удалена.")
        else:
            printy(message.chat.id, "Вы не были записаны на ближайшую сдачу.")

    except Exception as e:
        print("Ошибка при удалении записи из БД", e)
        printy(message.chat.id, "Не удалось удалить запись.")
    finally:
        con.close()

def see_entries(message):
    con, cur = connect_to_db()
    try:
        cur.execute("""
            SELECT baseReg.name, baseEntry.time
            FROM baseEntry
            JOIN baseReg ON baseEntry.user_id = baseReg.user_id
        """)
        entries = cur.fetchall()

        if not entries:
            printy(message.chat.id, "Список записей пуст.")
        else:
            response = "Текущие записи:\n"
            for idx, (name, time) in enumerate(entries, start=1):
                response += f"{idx}. {time} - Записан {name}. \n"
            
            printy(message.chat.id, response)

        con.close()
    except Exception as e:
        print("Ошибка при чтении из БД", e)
        printy(message.chat.id, "Не удалось загрузить список записей.")

def entry(message):
    time = datetime.now()

    con, cur = connect_to_db()
    try:
        cur.execute("SELECT * FROM baseEntry WHERE user_id = ?", (message.chat.id,))
        result = cur.fetchone()

        if result:
            printy(message.chat.id, "Вы уже записаны на ближайшую сдачу.")
        else:
            cur.execute("SELECT name FROM baseReg WHERE user_id = ?", (message.chat.id,))
            user_info = cur.fetchone()

            if user_info:
                user_name = user_info[0]

                cur.execute(
                    "INSERT INTO baseEntry (time, user_id) VALUES (?, ?)",
                    (str(time).split()[1], message.chat.id)
                )
                con.commit()
                printy(message.chat.id, f"Записал на {time}")
            else:
                printy(message.chat.id, "Вы не зарегистрированы. Пожалуйста, пройдите регистрацию.")
        
        con.close()
    except BaseException as e:
        print("Ошибка заполнения БД", e)
        printy(message.chat.id, "Произошла ошибка, попробуйте позже.")


@bot.message_handler(content_types=["text"])
def check_text_message(message):
    last_run_time = get_last_run_time()

    if last_run_time and message.date < last_run_time:
        return

    if message.text == "Информация о боте":
        printy(message.chat.id, "Бот для записи на сдачу лаб")
        printy(message.chat.id, "Создатель бота: https://t.me/Mr_GoldSky")
    elif message.text == "Назад":
        return interface(message)
    elif message.text == "Регистрация":
        return registration(message)
    elif message.text == "Записаться на ближайшую сдачу":
        return entry(message)
    elif message.text == "Посмотреть список":
        return see_entries(message)
    elif message.text == "Очистить записи" and message.chat.id == int(OWNER):
        return clear_entries(message)
    elif message.text == "Удалить свою запись":
        return clear_entrie(message)
    elif message.text == "Я уже зарегистрирован":
        return interface(message)



def startBot():
    update_last_run_time()
    bot.polling(none_stop=True)

startBot()
