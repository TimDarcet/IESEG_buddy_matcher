import json
import pandas as pd
import smtplib, ssl
from unidecode import unidecode
import click


@click.command()
@click.option("--port", '-p',
              type=int,
              default=587,
              help="SMTP port to use")
@click.option("--server", '-s',
              type=str,
              default="smtp.gmail.com",
              help="SMTP server to use")
@click.option("--sender-email", '-e',
              type=str,
              default="club.inter@gmail.com",
              help="email adress to use")
@click.option("--copy-to", '-c',
              type=str,
              multiple=True,
              help="E-mail addresses to put in copy of sent mails")
@click.option("--matches-file", '-m',
              type=click.File(),
              default="./output/matchings.csv",
              help="Input file containing the matches")
@click.option("--config-file", '-conf',
              type=click.File(),
              default="./config.json",
              help="JSON config file")
@click.option("--pwd-file", '-p',
              type=click.File(),
              help="File containing the SMTP password. \
                    If not provided, will prompt for password")
def sendMails(port, smtp_server, sender_email, copy_to, matches_file, config_file, pwd_file):
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        if not pwd_file:
            pwd_file = input("Enter your e-mail password : ")
        server.login(sender_email, pwd_file)

        def send(body, dests):
            server.sendmail(sender_email, ';'.join(dests), unidecode(body))
        matches = pd.read_csv(matches_file)
        config = json.load(config_file)
        for i, m in matches.iterrows():
            send(config["mails"][m["language"]].format(**m.to_dict()), [] + copy_to)
            # send(config["mails"][m["language"]].format(**m.to_dict()), [m["exEMail", m["frEMail"]] + copy_to)
