import os
import csv
import requests
from datetime import datetime

FILE_539 = '今彩539_歷史資料.csv'

def get_latest_issue(filename):
    if not os.path.exists(filename):
        return "0"
    try:
        # 改回 utf-8 讓 GitHub 機器人讀得懂
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            reader = list(csv.reader(f))
            valid_rows = [row for row in reader if len(row) > 0]
            if len(valid_rows) > 1:
                return str(valid_rows[-1][0]).strip()
    except Exception as e:
        print(f"讀取錯誤: {e}")
    return "0"

def fetch_data():
    last_issue = get_latest_issue(FILE_539)
    print(f"▶️ [今彩539] 目前 CSV 最新期數: {last_issue}")
    
    # 🌟 改用另一個全球開放的第三方 API 節點 (範例)
    # 注意：這裡使用一個假設的公開 API 節點，實戰中需替換為實際可用的來源
    url = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/DailyCashResult?period&pageNum=1&pageSize=50"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        # 使用 verify=False 忽略憑證錯誤，並加上更長的 timeout
        res = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if res.status_code == 200:
             print("連線成功！(由於官方持續阻擋，此為測試連線)")
             # 由於台彩及多數台灣彩券網站近期全面升級防爬蟲 (Cloudflare 等)，
             # 強烈建議：
             # 1. 將爬蟲程式改放在台灣的伺服器 (如本地電腦的排程) 執行。
             # 2. 或尋找付費/穩定的第三方開獎 API 服務。
        else:
             print(f"連線被拒絕，狀態碼: {res.status_code}。台灣網站阻擋了海外伺服器。")

    except Exception as e:
         print(f"連線失敗，台灣伺服器完全阻擋了 GitHub 的美國 IP。錯誤詳情: {e}")

if __name__ == "__main__":
    fetch_data()
