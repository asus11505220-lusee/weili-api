import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.taiwanlottery.com/",
}

# 你CSV最後一筆是115000047，查下一期115000048（如果已開獎）
# 也順便查前一期115000047確認結構與既有資料吻合
url = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/SuperLotto638Result"

for period in ["115000047", "115000048", "115000049"]:
    print(f"===== 威力彩 period={period} =====")
    try:
        r = requests.get(url, params={"period": period}, headers=HEADERS, timeout=15)
        print("status:", r.status_code)
        body = r.json()
        print("rtCode:", body.get("rtCode"))
        content = body.get("content") or {}
        res = content.get("superLotto638Res")
        if res:
            print(json.dumps(res[0], ensure_ascii=False, indent=2))
        else:
            print("no data, content keys:", list(content.keys()))
    except Exception as e:
        print("錯誤:", e)
    print()
