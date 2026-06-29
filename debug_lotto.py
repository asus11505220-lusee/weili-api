import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.taiwanlottery.com/",
}

url = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/LottoResult"

# 查詢最近幾期（你CSV最後一期是115000065）
for period in ["115000064", "115000065", "115000066"]:
    print(f"===== 大樂透 period={period} =====")
    try:
        r = requests.get(url, params={"period": period}, headers=HEADERS, timeout=15)
        print("status:", r.status_code)
        body = r.json()
        print("rtCode:", body.get("rtCode"))
        content = body.get("content") or {}
        print("content keys:", list(content.keys()))
        # 找所有可能的資料key
        for key, val in content.items():
            if val and key != "totalSize":
                print(f"{key}:")
                print(json.dumps(val[0] if isinstance(val, list) else val, ensure_ascii=False, indent=2))
    except Exception as e:
        print("錯誤:", e)
    print()
