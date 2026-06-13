import requests
import json
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.taiwanlottery.com/",
}

url = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result"

today = datetime.now()

# 嘗試多種日期格式參數
attempts = [
    {"name": "month=YYYY-MM", "params": {"month": today.strftime("%Y-%m")}},
    {"name": "month=YYYY-MM-01", "params": {"month": today.strftime("%Y-%m-01")}},
    {"name": "month=YYYY/MM", "params": {"month": today.strftime("%Y/%m")}},
    {"name": "startDate&endDate", "params": {
        "startDate": today.strftime("%Y-%m-01"),
        "endDate": today.strftime("%Y-%m-%d"),
    }},
    {"name": "period=最新一期猜測115000143", "params": {"period": "115000143"}},
    {"name": "pageNum=1 pageSize=1 only", "params": {"pageNum": 1, "pageSize": 1}},
]

for a in attempts:
    print(f"===== {a['name']} =====")
    print("params:", a["params"])
    try:
        r = requests.get(url, params=a["params"], headers=HEADERS, timeout=15)
        print("status:", r.status_code)
        body = r.json()
        # 只印關鍵欄位，避免log太長
        content = body.get("content")
        print("rtCode:", body.get("rtCode"), "rtMsg:", body.get("rtMsg"))
        if content:
            print("totalSize:", content.get("totalSize"))
            res = content.get("daily539Res")
            if res:
                print("daily539Res (前2筆):", json.dumps(res[:2], ensure_ascii=False, indent=2))
            else:
                print("daily539Res:", res)
        else:
            print("content:", content)
    except Exception as e:
        print("錯誤:", e)
    print()
