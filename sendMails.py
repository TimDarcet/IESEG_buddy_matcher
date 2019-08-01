import json
import pandas as pd
import smtplib, ssl
from unidecode import unidecode

port = 587  # For starttls
smtp_server = "smtp.gmail.com"
sender_email = "club.inter@gmail.com"


context = ssl.create_default_context()
with smtplib.SMTP(smtp_server, port) as server:
    server.starttls(context=context)
    server.login(input("Enter your gmail adress : "),
                 input("Enter your e-mail password : "))
    
    def send(body, dests):
        server.sendmail(sender_email, ';'.join(dests), unidecode(body))

    matches = pd.read_csv("./output/matchings.csv")
    with open("./config.json", "r") as conf_file:
        config = json.load(conf_file)

    for i, m in matches.iterrows():
        send(config["mails"][m["language"]].format(**m.to_dict()), ["timothee.darcet@gmail.com"])

# cikvibjgnvyqukyh