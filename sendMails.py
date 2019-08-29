import json
import pandas as pd
import smtplib, ssl
from unidecode import unidecode
import click
from sys import stderr


@click.command()
@click.option("--port", '-p',
              type=int,
              default=587,
              help="SMTP port to use")
@click.option("--smtp-server", '-s',
              type=str,
              default="smtp.gmail.com",
              help="SMTP server to use")
@click.option("--sender-email", '-e',
              type=str,
              default="international.club.ieseg@gmail.com",
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
@click.option("--dry", '-d',
              is_flag=True,
              help="Do not actually send emails")
@click.option("--verbose", '-v',
              count=True,
              help="Show more info in stderror")
def send_mails(port,
               smtp_server,
               sender_email,
               copy_to,
               matches_file,
               config_file,
               pwd_file,
               dry,
               verbose):
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        if not pwd_file:
            pwd = input("Enter your e-mail password : ")
        else:
            pwd = pwd_file.read().strip()
        server.login(sender_email, pwd)

        def send(body, dests):
            server.sendmail(sender_email, ';'.join(dests), unidecode(body))
        matches = pd.read_csv(matches_file)
        config = json.load(config_file)
        for i, m in matches.iterrows():
            if verbose > 0:
                print("Sending to ", m["exEMail"], "and", m["frEMail"],
                      file=stderr)
            if not dry:
                send(config["mails"][m["language"]].format(**m.to_dict()),
                     [] + list(copy_to))
            # send(config["mails"][m["language"]].format(**m.to_dict()),
            #      [m["exEMail"], m["frEMail"]] + list(copy_to))
