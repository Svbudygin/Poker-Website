import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from random import randint


def send_email(to_mail, code):
    sender = "pokerdsba@gmail.com"
    template = None
    try:
        with open("templates/email_template.html") as file:
            template = file.read()
    except IOError:
        return "The template file doesn't found!"
    password = "jprs vssq lodd hthg"

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    try:
        msg = MIMEMultipart()
        server.login(sender, password)
        msg["From"] = sender
        msg["To"] = to_mail

        msg.attach(MIMEText(template, "html"))
        msg.attach(MIMEText(str(code)))
        msg["Subject"] = "Mail confirmation"
        server.sendmail(sender, to_mail, msg.as_string())
        return "The message was sent successfully!"
    except Exception as _ex:
        return f"{_ex}\nCheck your login or password please!"


def main():
    print(send_email())


if __name__ == "__main__":
    main()
