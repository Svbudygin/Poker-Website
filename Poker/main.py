import sqlite3

# Устанавливаем соединение с базой данных
conn = sqlite3.connect("data/users.sql")
cursor = conn.cursor()

# Изменяем статус пользователя на "Admin" для id=1
cursor.execute('UPDATE users SET status=? WHERE id=?', ('Admin', 1))

# Подтверждаем изменения
conn.commit()

# Закрываем соединение
conn.close()
