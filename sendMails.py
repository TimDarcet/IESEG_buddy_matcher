import json
import pandas as pd

def send(body, dests):
    pass

matches = pd.read_csv("./output/matchings.csv")
with open("./config.json", "r") as conf_file:
    config = json.load(conf_file)

for m in matches:
    print(m)
