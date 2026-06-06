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
        with open(filename, 'r', encoding='utf-8') as f:
            reader = list(csv.reader(f))
            if len(reader) > 1:
                return str(reader[-1][0])
    except Exception as e:
        print(f"讀取錯誤: {e}")
    return "0"

def run_real_crawler():
    last_issue = get_latest_issue(FILE_539)
    print(f"目前 CSV 最新期數為: {last_issue}")
    
    # 🌟 使用台彩官方隱藏版的 JSON API 🌟
    today_month = datetime.now().strftime("%Y-%m")
    url = f"https://api.taiwanlottery.com/TLCAPIWeB/Lottery/DailyCashResult?period&month={today_month}&pageNum=1&pageSize=50"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        # 解析台彩回傳的純淨資料庫格式
        if "content" in data and "dailyCashRes" in data["content"] and len(data["content"]["dailyCashRes"]) > 0:
            # 取第一筆 (最新的一期)
            latest_draw = data["content"]["dailyCashRes"][0] 
            
            # 取得官方期數
            fetched_issue = str(latest_draw["period"])
            
            # 處理官方日期 (將 2026-06-06T00:00:00 轉為 2026/06/06)
            raw_date = latest_draw["lotteryDate"].split("T")[0]
            fetched_date = raw_date.replace("-", "/")
            
            # 取得官方開出號碼 (已經是從小到大排序好的陣列)
            fetched_numbers = latest_draw["drawNumberSize"]
            # 確保數字前面會自動補 0，例如 "5" 變成 "05"
            fetched_numbers = [str(n).zfill(2) for n in fetched_numbers]
            
            print(f"📡 從台彩 API 抓到最新期數: {fetched_issue}, 號碼: {fetched_numbers}")
            
            # 判斷是否需要寫入
            if fetched_issue > last_issue:
                # 自動計算總和
                total_sum = sum(int(num) for num in fetched_numbers)
                
                # 組合完美的一列
                new_row = [fetched_issue, fetched_date] + fetched_numbers + [str(total_sum)]
                
                with open(FILE_539, 'a', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow(new_row)
                print(f"✅ 成功將第 {fetched_issue} 期真實號碼補進 CSV 啦！")
            else:
                print("目前的 CSV 已經是最新的，無須重複更新。")
        else:
            print("無法從台彩 API 找到當月資料。")

    except Exception as e:
        print(f"爬取或連線失敗: {e}")

if __name__ == "__main__":
    run_real_crawler()
