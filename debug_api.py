import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

urls = {
    "539": "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result",
    "威力彩": "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/SuperLotto638Result",
}

for name, url in urls.items():
    print(f"===== {name} =====")
    try:
        resp = requests.get(url, params={"period": "", "pageNum": 1, "pageSize": 2}, headers=HEADERS, timeout=15)
        print("status:", resp.status_code)
        print(json.dumps(resp.json(), ensure_ascii=False, indent=2)[:3000])
    except Exception as e:
        print("錯誤:", e)
    print()
