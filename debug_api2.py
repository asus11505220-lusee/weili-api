import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.taiwanlottery.com/",
}

# ---- 今彩539 ----
print("===== 539 (帶 month 參數) =====")
url = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result"
params = {"period": "", "month": "202606", "pageNum": 1, "pageSize": 5}
try:
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    print("status:", r.status_code)
    print(json.dumps(r.json(), ensure_ascii=False, indent=2)[:2000])
except Exception as e:
    print("錯誤:", e)

print()
print("===== 539 (無參數) =====")
try:
    r = requests.get(url, headers=HEADERS, timeout=15)
    print("status:", r.status_code)
    print(json.dumps(r.json(), ensure_ascii=False, indent=2)[:2000])
except Exception as e:
    print("錯誤:", e)

# ---- 嘗試另一個常見的台彩開獎結果API ----
print()
print("===== 嘗試 LotteryResult API =====")
url2 = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/PCSOLatestResult"
try:
    r = requests.get(url2, headers=HEADERS, timeout=15)
    print("status:", r.status_code)
    print(r.text[:1500])
except Exception as e:
    print("錯誤:", e)

# ---- 嘗試取得首頁，找最新一期的線索 ----
print()
print("===== 嘗試首頁 result/lotto539 =====")
url3 = "https://www.taiwanlottery.com/lotto/result/lotto539"
try:
    r = requests.get(url3, headers=HEADERS, timeout=15)
    print("status:", r.status_code)
    print("length:", len(r.text))
    print(r.text[:1000])
except Exception as e:
    print("錯誤:", e)
