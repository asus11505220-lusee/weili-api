import os
import csv
import requests
from datetime import datetime

FILE_539 = '今彩539_歷史資料.csv'

def get_latest_issue(filename):
    """讀取我們 CSV 目前最後一期的期數"""
    if not os.path.exists(filename):
        return "0"
    try:
        # 🌟 關鍵修正 1：用 big5 解碼，解決 Excel 亂碼問題，讓機器人看得懂！
        with open(filename, 'r', encoding='big5', errors='ignore') as f:
            reader = list(csv.reader(f))
            # 濾除可能出現的空白行
            valid_rows = [row for row in reader if len(row) > 0]
            if len(valid_rows) > 1:
                return str(valid_rows[-1][0]).strip()
    except Exception as e:
        print(f"讀取 CSV 發生錯誤: {e}")
    return "0"

def run_real_crawler():
    last_issue = get_latest_issue(FILE_539)
    print(f"目前 CSV 最新期數為: {last_issue}")
    
    # 呼叫台彩官方隱藏版 API
    today_month = datetime.now().strftime("%Y-%m")
    url = f"https://api.taiwanlottery.com/TLCAPIWeB/Lottery/DailyCashResult?period&month={today_month}&pageNum=1&pageSize=50"
    
    # 🌟 關鍵修正 2：加強偽裝，避免台彩阻擋 GitHub 的美國伺服器
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Origin': 'https://www.taiwanlottery.com.tw',
        'Referer': 'https://www.taiwanlottery.com.tw/'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"連線失敗！台彩可能擋住了海外 IP。狀態碼: {response.status_code}")
            return
            
        data = response.json()
        
        # 解析台彩回傳的資料
        if "content" in data and "dailyCashRes" in data["content"] and len(data["content"]["dailyCashRes"]) > 0:
            latest_draw = data["content"]["dailyCashRes"][0] 
            fetched_issue = str(latest_draw["period"])
            
            # 將日期格式轉換
            raw_date = latest_draw["lotteryDate"].split("T")[0]
            fetched_date = raw_date.replace("-", "/")
            
            # 取得號碼並補零 (例如 5 變成 05)
            fetched_numbers = latest_draw["drawNumberSize"]
            fetched_numbers = [str(n).zfill(2) for n in fetched_numbers]
            
            print(f"📡 從台彩 API 抓到最新期數: {fetched_issue}, 號碼: {fetched_numbers}")
            
            # 比對期數，確認是新資料才寫入
            if fetched_issue > last_issue:
                total_sum = sum(int(num) for num in fetched_numbers)
                new_row = [fetched_issue, fetched_date] + fetched_numbers + [str(total_sum)]
                
                # 🌟 寫入時也強制使用 big5，保證你用 Excel 看依然完美無瑕！
                with open(FILE_539, 'a', newline='', encoding='big5', errors='ignore') as f:
                    csv.writer(f).writerow(new_row)
                print(f"✅ 成功將第 {fetched_issue} 期真實號碼補進 CSV！")
            else:
                print("目前的 CSV 已經是最新的，無須重複更新。")
        else:
            print("無法從台彩 API 找到當月資料。")

    except Exception as e:
        print(f"爬取或連線發生重大錯誤: {e}")

if __name__ == "__main__":
    run_real_crawler()
