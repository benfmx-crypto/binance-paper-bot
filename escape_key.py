import json

with open("binance-trading-bot-1-456809-852313cbe9b7.json") as f:
    key = json.load(f)

key["private_key"] = key["private_key"].replace("\n", "\\n")

print("GOOGLE_SHEETS_CREDS = '''")
print(json.dumps(key, indent=2))
print("'''")
