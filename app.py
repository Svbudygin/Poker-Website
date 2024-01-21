import re
import secrets
import sqlite3
from datetime import datetime
from random import randint
from time import sleep

from flask import Flask, request, render_template, url_for, session, redirect

from mailsender import send_email

import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
# app.config['SERVER_NAME'] = '127.0.0.1:8080'
admins = {1, "1"}
app.config['UPLOAD_FOLDER_NOT_USERS'] = 'static/uploadsnotusers'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}


@app.errorhandler(404)
def page_not_found(e):
    return render_template('mistake.html'), 404


@app.route('/lk', methods=['GET', 'POST'])
def lk():
    loginin = session.get('user_id')
    coloradmin = False
    if bool(loginin):
        coloradmin = bool(session.get('user_id') in admins)
        if coloradmin:
            return redirect(url_for('games'))
    else:
        return redirect(url_for('games'))

    conn = sqlite3.connect("data/users.sql")
    cursor = conn.cursor()
    cursor.execute('SELECT fullname, phone, email, password  FROM users WHERE id=?', (loginin,))
    users = cursor.fetchone()
    info_about_user = {}
    if users:
        fullname, phone, email, password = users
        info_about_user = {
            "fullname": fullname,
            "phone": phone,
            "user_id": loginin,
            "email": email,
            "password": password,
        }

    if request.method == "POST":
        all_args = request.form
        if all_args:
            newName = all_args.get("newName")
            newEmail = all_args.get("newEmail")
            newPhone = all_args.get("newPhone")
            newPassword = all_args.get("newPassword")
            confirmPassword = all_args.get("confirmPassword")
            if confirmPassword != newPassword:
                cursor.close()
                conn.close()
                return redirect(url_for('lk'))
            hashed_password = generate_password_hash(newPassword.strip())
            cursor.execute(
                'UPDATE users SET fullname=?, phone=?, email=?, password=? WHERE id=?',
                (newName, newPhone, newEmail, hashed_password, loginin))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('games'))
    cursor.close()
    conn.close()
    return render_template('lk.html', background=False, loginin=bool(loginin), coloradmin=coloradmin,
                           info_about_user=info_about_user)


def correct_dates(date):
    try:
        execttime = re.split('T|\.', date)[1][:-3] + ' '
    except IndexError:
        execttime = ''
    deadline = datetime(*map(int, re.split('-|:|T', date)[:5]))
    return f"{deadline.strftime('%d.%m.%Y')} {deadline.strftime('%H:%M')}"


def allowed_file(filename):
    return filename.split('.')[-1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        fullname = request.form['fullname']
        phone = request.form['phone']
        # try:
        #     if int(phone) and len(phone) != 11:
        #         raise Exception
        # except:
        #     return render_template('register.html', background=True, loginin=False)
        email = request.form['email']
        password1 = request.form['password1']
        if not os.path.exists("data"):
            os.mkdir("data")
        conn = sqlite3.connect("data/users.sql")
        cursor = conn.cursor()
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, fullname VARCHAR(200), phone VARCHAR(200), email VARCHAR(200), password VARCHAR(200),status VARCHAR(200) )')

        cursor.execute('SELECT phone, email, id FROM users ')
        users = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if users:
            users_phone, users_email, id = users
            if phone in users_phone or email in users_email:
                return redirect(url_for('login'))
        conn = sqlite3.connect("data/notusers.sql")
        cursor = conn.cursor()
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS notusers (id INTEGER PRIMARY KEY AUTOINCREMENT, fullname VARCHAR(200), phone VARCHAR(200), email VARCHAR(200), password VARCHAR(200),filename VARCHAR(200), code VARCHAR(200) )')

        hashed_password = generate_password_hash(password1.strip())
        code = randint(100_000, 100_000_0 - 1)
        print("code randint:", code)
        send_email(email, code)
        file = request.files.get('profilepic')
        filename = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            folder = app.config['UPLOAD_FOLDER_NOT_USERS']
            if not os.path.exists(folder):
                os.mkdir(folder)
            file.save(os.path.join(folder, filename))

        cursor.execute(
            f'INSERT OR REPLACE INTO notusers (fullname, phone, email, password, filename, code) VALUES (?,?, ?, ?, ?,?)',
            (fullname, phone, email, hashed_password, filename, code))
        cursor.execute('SELECT id FROM notusers WHERE email=? ', (email,))
        user_id = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if user_id:
            session['notuser_id'] = user_id[0]

        return redirect(url_for('register2'))
    return render_template('register.html', background=True, loginin=False)


def process_file(input_path, output_folder, new_filename):
    # Открываем файл
    with open(input_path, 'rb') as file:
        data = file.read()

    # Сохраняем файл в другом месте
    with open(os.path.join(output_folder, new_filename), 'wb') as new_file:
        new_file.write(data)

    # Удаляем исходный файл
    os.remove(input_path)


@app.route('/register2', methods=['GET', 'POST'])
def register2():
    if not session.get('notuser_id'):
        return redirect(url_for('games'))
    if request.method == "POST":
        inputcode = request.form['code']
        notuserid = session.get('notuser_id')
        conn1 = sqlite3.connect("data/notusers.sql")
        cursor1 = conn1.cursor()
        cursor1.execute(
            'CREATE TABLE IF NOT EXISTS notusers (id INTEGER PRIMARY KEY AUTOINCREMENT, fullname VARCHAR(200), phone VARCHAR(200), email VARCHAR(200), password VARCHAR(200),filename VARCHAR(200) )')

        cursor1.execute('SELECT fullname, phone, email, password, filename, code FROM notusers WHERE id=?', (notuserid,))
        all_user = cursor1.fetchone()
        folder = app.config['UPLOAD_FOLDER_NOT_USERS']
        if all_user:
            fullname, phone, email, hashed_password, filename, code = all_user
            print("code input:", code," - ", inputcode)
            if str(inputcode) != str(code):
                cursor1.close()
                conn1.close()
                return redirect(url_for('register2'))
            cursor1.execute(f"DELETE FROM notusers WHERE id = ?", (notuserid,))
            conn1.commit()
            cursor1.close()
            conn1.close()
            conn = sqlite3.connect("data/users.sql")
            cursor = conn.cursor()
            cursor.execute(
                'CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, fullname VARCHAR(200), phone VARCHAR(200), email VARCHAR(200), password VARCHAR(200),status VARCHAR(200) )')

            cursor.execute('SELECT phone, email, id FROM users ')
            users = cursor.fetchone()
            if users:
                users_phone, users_email, id = users
                if phone in users_phone or email in users_email:
                    conn.commit()
                    cursor.close()
                    conn.close()
                    return redirect(url_for('login'))

            cursor.execute(
                f'INSERT OR REPLACE INTO users (fullname, phone, email, password, status) VALUES (?,?, ?, ?, ?)',
                (fullname, phone, email, hashed_password, "Guest"))
            cursor.execute('SELECT id FROM users WHERE email=? ', (email,))
            user_id = cursor.fetchone()
            session['user_id'] = user_id
            process_file(folder + "/" + filename, app.config['UPLOAD_FOLDER'], str(user_id[0]) + ".png")
            conn.commit()
            cursor.close()
            conn.close()
        else:
            cursor1.close()
            conn1.close()
        return redirect(url_for('games'))
    return render_template('register2.html', background=True, loginin=False)


@app.route('/register82', methods=['GET', 'POST'])
def register9():
    if request.method == "POST":
        fullname = request.form['fullname']
        phone = request.form['phone']
        try:
            if int(phone) and len(phone) != 11:
                raise Exception
        except:
            return render_template('register.html', background=True, loginin=False)
        email = request.form['email']
        password1 = request.form['password1']
        if not os.path.exists("data"):
            os.mkdir("data")
        conn = sqlite3.connect("data/users.sql")
        cursor = conn.cursor()
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, fullname VARCHAR(200), phone VARCHAR(200), email VARCHAR(200), password VARCHAR(200),status VARCHAR(200) )')

        cursor.execute('SELECT phone, email, id FROM users ')
        users = cursor.fetchone()
        if users:
            users_phone, users_email, id = users
            if phone in users_phone or email in users_email:
                conn.commit()
                cursor.close()
                conn.close()
                return redirect(url_for('login'))
        hashed_password = generate_password_hash(password1.strip())
        send_email(email)
        sleep(120)
        cursor.execute(f'INSERT OR REPLACE INTO users (fullname, phone, email, password, status) VALUES (?,?, ?, ?, ?)',
                       (fullname, phone, email, hashed_password, "Guest"))
        cursor.execute('SELECT id FROM users WHERE email=? ', (email,))
        user_id = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        session['user_id'] = user_id
        file = request.files.get('profilepic')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            folder = app.config['UPLOAD_FOLDER']
            if not os.path.exists(folder):
                os.mkdir(folder)
            file.save(os.path.join(folder, str(user_id[0]) + ".png"))
        return redirect(url_for('games'))
    return render_template('register.html', background=True, loginin=False)


@app.route('/')
@app.route('/games')
def games():
    if not os.path.exists("data"):
        os.mkdir("data")
    user_id = session.get('user_id')
    conn = sqlite3.connect('data/games.sql')
    cursor = conn.cursor()
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, participants VARCHAR(200), buy_in VARCHAR(200), bb_sb VARCHAR(200), extra_fee_food VARCHAR(200), extra_fee_alcohol VARCHAR(200), phone_number VARCHAR(200), date_and_time VARCHAR(200), location VARCHAR(2000), players VARCHAR(2000))')

    current_date = datetime.now()
    current_date_str = current_date.strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute(f"DELETE FROM games WHERE date_and_time < '{current_date_str}'")

    cursor.execute(
        'SELECT participants, buy_in, bb_sb, extra_fee_food, extra_fee_alcohol, phone_number, date_and_time, location,players FROM games')
    users = cursor.fetchall()
    list_all_games = []
    if users:
        for user in users:
            participants, buy_in, bb_sb, extra_fee_food, extra_fee_alcohol, phone_number, date_and_time, location, players = user
            dict_game = {
                "participants": participants,
                "buy_in": buy_in,
                "bb_sb": bb_sb,
                "extra_fee_food": extra_fee_food,
                "extra_fee_alcohol": extra_fee_alcohol,
                "phone_number": phone_number,
                "exact_date": date_and_time,
                "date_and_time": correct_dates(date_and_time),
                "players": len(players.split('/')),
                "location": location
            }
            list_all_games.append(dict_game)
    if list_all_games:
        list_all_games.sort(key=lambda x: x['exact_date'])
    conn.commit()
    cursor.close()
    conn.close()
    loginin = bool(session.get('user_id'))
    coloradmin = False
    if loginin:
        coloradmin = bool(session.get('user_id') in admins)
    status = 'None'
    if user_id:
        conn = sqlite3.connect("data/users.sql")
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM users WHERE id=? ', (str(user_id),))
        status = cursor.fetchone()
        if status:
            status = status[0]
        cursor.close()
        conn.close()
    return render_template('games.html', background=True, loginin=loginin, status=status,
                           coloradmin=coloradmin, list_all_games=list_all_games)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('games'))


def get_vip_ids():
    conn = sqlite3.connect("data/users.sql")
    cursor = conn.cursor()
    cursor.execute(f"SELECT id FROM users WHERE status = ?", ('Vip',))
    ids_vip = cursor.fetchall()
    cursor.close()
    conn.close()
    if ids_vip:
        return list(map(lambda x: str(x[0]), ids_vip))
    return []


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    games_all = []
    id_to_del = request.args.get('delete')

    if not os.path.exists("data"):
        os.mkdir("data")
    conn = sqlite3.connect("data/games.sql")
    cursor = conn.cursor()
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, participants VARCHAR(200), buy_in VARCHAR(200), bb_sb VARCHAR(200), extra_fee_food VARCHAR(200),extra_fee_alcohol VARCHAR(200) ,phone_number VARCHAR(200),date_and_time VARCHAR(200), location VARCHAR(2000), players VARCHAR(2000))')
    if id_to_del:
        cursor.execute(f"DELETE FROM games WHERE id = ?", (int(id_to_del),))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('admin'))
    if request.method == "POST":
        participants = request.form['participants']
        ids_vip = get_vip_ids()[:int(participants)]
        ids_vip = "/".join(ids_vip)
        buy_in = request.form['buy_in']
        bb_sb = request.form['bb_sb']
        extra_fee_food = request.form['extra_fee']
        extra_fee_alcohol = request.form['extra_fee_alc']
        phone_number = request.form['phone_number']
        date_and_time = request.form['date']
        location = request.form['location']
        cursor.execute(
            f'INSERT OR REPLACE INTO games (participants, buy_in, bb_sb, extra_fee_food,extra_fee_alcohol,phone_number,date_and_time, location, players) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (participants, buy_in, bb_sb, extra_fee_food, extra_fee_alcohol, phone_number, date_and_time, location,
             ids_vip))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('games'))
    cursor.execute('SELECT id, date_and_time from games')
    games_all = cursor.fetchall()
    conn.commit()
    cursor.close()
    conn.close()
    loginin = bool(session.get('user_id'))
    coloradmin = False
    if loginin:
        coloradmin = bool(session.get('user_id') in admins)
    if not coloradmin in admins:
        return redirect(url_for('games'))

    return render_template('admin.html', background=True, loginin=True, coloradmin=True, games_all=games_all)


def get_status_lst_players(loginin, user_ids):
    conn = sqlite3.connect("data/users.sql")
    cursor = conn.cursor()
    lst_players = []

    for user_id in user_ids:
        cursor.execute('SELECT id, fullname FROM users WHERE id=?', (user_id,))
        user_info = cursor.fetchone()
        lst_players.append(user_info)
    cursor.execute('SELECT status FROM users WHERE id=?', (loginin,))
    status = cursor.fetchone()
    if status:
        status = status[0]
    conn.commit()
    cursor.close()
    conn.close()
    return status, lst_players


def deleating(id_to_del):
    conn = sqlite3.connect('data/games.sql')
    cursor = conn.cursor()
    cursor.execute('SELECT players, date_and_time, id  FROM games')
    users = cursor.fetchall()
    list_all_games = []
    for players in users:
        list_all_games.append(
            {"players": players[0], 'exact_date': players[1], "id": players[2]})
    if list_all_games:
        list_all_games.sort(key=lambda x: x['exact_date'])
    user_ids = []

    if list_all_games:
        user_ids_before = list_all_games[0]["players"]
        for i in user_ids_before.split("/"):
            try:
                user_ids.append(str(int(i)))
                if i in admins:
                    raise ValueError
            except ValueError:
                pass
        user_ids = set(user_ids) - {id_to_del}
        user_str_id = "/".join(user_ids)

        cursor.execute(f"UPDATE games SET players = ? WHERE id = ?", (user_str_id, list_all_games[0]["id"]))
    conn.commit()
    cursor.close()
    conn.close()
    return user_ids


def players_for_next_game(playerid):
    conn = sqlite3.connect('data/games.sql')
    cursor = conn.cursor()
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT, participants VARCHAR(200), buy_in VARCHAR(200), bb_sb VARCHAR(200), extra_fee_food VARCHAR(200), extra_fee_alcohol VARCHAR(200), phone_number VARCHAR(200), date_and_time VARCHAR(200), location VARCHAR(2000), players VARCHAR(2000))')

    current_date = datetime.now()
    current_date_str = current_date.strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute(f"DELETE FROM games WHERE date_and_time < '{current_date_str}'")
    cursor.execute('SELECT players,participants, date_and_time, id  FROM games')
    users = cursor.fetchall()
    list_all_games = []
    for players in users:
        list_all_games.append(
            {"players": players[0], 'exact_date': players[2], "participants": players[1], "id": players[3]})
    if list_all_games:
        list_all_games.sort(key=lambda x: x['exact_date'])
    user_ids = []

    if list_all_games:
        user_ids_before = list_all_games[0]["players"]
        for i in user_ids_before.split("/"):
            try:
                user_ids.append(str(int(i)))
                if i in admins:
                    raise ValueError
            except ValueError:
                pass
        if playerid:
            participants = list_all_games[0]["participants"]
            user_id = set(user_ids)
            if len(user_id) < int(participants):
                user_id.add(str(playerid))

            user_ids = []
            for i in user_id:
                try:
                    user_ids.append(str(int(i)))
                    if i in admins:
                        raise ValueError
                except ValueError:
                    pass
            user_str_id = "/".join(user_ids)
            cursor.execute(f"UPDATE games SET players = ? WHERE id = ?", (user_str_id, list_all_games[0]["id"]))
    conn.commit()
    cursor.close()
    conn.close()
    return (user_ids, int(list_all_games[0]["participants"]) - len(user_ids)) if list_all_games else (user_ids, 0)


@app.route('/nextgame')
def nextgame():
    coloradmin = bool(session.get('user_id') in admins)
    loginin = session.get('user_id')
    playerid = request.args.get("player")
    id_to_delete = request.args.get("delete")
    if id_to_delete and (str(loginin) == str(id_to_delete) or coloradmin):
        deleating(id_to_delete)
        return redirect(url_for('nextgame'))
    user_ids, remains = players_for_next_game(playerid)
    status, lst_players = get_status_lst_players(loginin, user_ids=user_ids)
    butmclick = not any(i[0] == loginin for i in lst_players)
    return render_template('nextgame.html', players=lst_players, loginin=bool(loginin), status=status, playerid=loginin,
                           coloradmin=coloradmin, remains=remains, butmclick=butmclick)


@app.route('/team')
def team():
    loginin = bool(session.get('user_id'))
    coloradmin = False
    if loginin:
        coloradmin = bool(session.get('user_id') in admins)
    conn = sqlite3.connect("data/users.sql")
    cursor = conn.cursor()
    cursor.execute('SELECT id, fullname, status FROM users')
    users = cursor.fetchall()
    list_all_members = []
    list_all_guests = []
    if users:
        for user in users:
            user_id, fullname, status = user
            if user_id not in admins:
                dict_user = {
                    "fullname": fullname,
                    "status": status,
                    "user_id": user_id,
                }
                if status in {'Vip', 'Member'}:
                    list_all_members.append(dict_user)
                else:
                    list_all_guests.append(dict_user)
    if list_all_members:
        list_all_members.sort(key=lambda x: 0 if x['status'] == 'Vip' else (1 if x['status'] == 'Member' else 2))
    if coloradmin:
        status = request.args.get('status')
        userid = request.args.get('userid')
        if status and userid:
            if status.lower() == "delete":
                cursor.execute(f"DELETE FROM users WHERE id = ?", (userid,))
            elif status.lower() == "vip" or status.lower() == "member":
                cursor.execute(f"UPDATE users SET status = ? WHERE id = ?", (status, userid))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('team'))
    conn.commit()
    cursor.close()
    conn.close()

    return render_template('team.html', background=True, loginin=loginin, coloradmin=coloradmin,
                           list_all_members=list_all_members, list_all_guests=list_all_guests)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['phonelog']
        password = request.form['passwordlog']
        conn = sqlite3.connect("data/users.sql")
        cursor = conn.cursor()
        cursor.execute('SELECT password, id FROM users WHERE email=? OR phone=? ', (username, username))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            user_password, user_id = user
            if user and check_password_hash(user_password, password):
                session['user_id'] = user_id
                return redirect(url_for('games'))
    return render_template('login.html', background=True, loginin=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
