import requests
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.taiwanlottery.com/",
}

# 嘗試各種可能的大樂透API endpoint
endpoints = [
    "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/LottoResult",
    "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/BigLottoResult",
    "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Lotto649Result",
    "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/DaLottoResult",
    "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Lotto638Result",
]

for url in endpoints:
    print(f"===== {url.split('/')[-1]} =====")
    try:
        r = requests.get(url, params={"period": "115000065"}, headers=HEADERS, timeout=10)
        print(f"status: {r.status_code}")
        if r.status_code == 200:
            print(r.text[:500])
        else:
            print(r.text[:200])
    except Exception as e:
        print(f"錯誤: {e}")
    print()

# 也試試不帶period參數
print("===== LottoResult 不帶參數 =====")
try:
    r = requests.get("https://api.taiwanlottery.com/TLCAPIWeB/Lottery/LottoResult", headers=HEADERS, timeout=10)
    print(f"status: {r.status_code}")
    print(r.text[:500])
except Exception as e:
    print(f"錯誤: {e}")
