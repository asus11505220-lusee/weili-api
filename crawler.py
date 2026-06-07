import os
import csv
import requests
from datetime import datetime

FILE_539 = '今彩539_歷史資料.csv'
FILE_WEILI = '威力彩_歷史資料.csv'

def get_latest_issue(filename):
    """讀取 CSV 取得最後一期期數"""
    if not os.path.exists(filename):
        return "0"
    try:
        with open(filename, 'r', encoding='big5', errors='ignore') as f:
            reader = list(csv.reader(f))
            valid_rows = [row for row in reader if len(row) > 0]
            if len(valid_rows) > 1:
                return str(valid_rows[-1][0]).strip()
    except Exception:
        pass
    return "0"

def fetch_539():
    last_issue = get_latest_issue(FILE_539)
    print(f"▶️ [今彩539] 目前 CSV 最新期數: {last_issue}")
    
    # 呼叫台彩官方 API
    today_month = datetime.now().strftime("%Y-%m")
    url = f"https://api.taiwanlottery.com/TLCAPIWeB/Lottery/DailyCashResult?period&month={today_month}&pageNum=1&pageSize=50"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Origin': 'https://www.taiwanlottery.com',
        'Referer': 'https://www.taiwanlottery.com/'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        data = res.json()
        
        results = data.get("content", {}).get("dailyCashRes", [])
        if not results:
            print("❌ [今彩539] API 回傳無資料")
            return
            
        latest_draw = results[0]
        fetched_issue = str(latest_draw["period"])
        
        # 處理日期 (2026-06-06T00:00:00 -> 2026/06/06)
        raw_date = latest_draw["lotteryDate"].split("T")[0]
        fetched_date = raw_date.replace("-", "/")
        
        # 處理號碼
        nums = latest_draw["drawNumberSize"]
        nums_str = [str(n) for n in nums]
        
        # 確認是新資料才寫入
        if int(fetched_issue) > int(last_issue):
            total_sum = sum(nums)
            new_row = [fetched_issue, fetched_date] + nums_str + [str(total_sum)]
            
            with open(FILE_539, 'a', newline='', encoding='big5', errors='ignore') as f:
                csv.writer(f).writerow(new_row)
            print(f"✅ [今彩539] 成功將第 {fetched_issue} 期真實號碼補進 CSV！")
        else:
            print("⏸️ [今彩539] 已是最新，無須更新。")
    except Exception as e:
        print(f"❌ [今彩539] 發生重大錯誤: {e}")

def fetch_weili():
    last_issue = get_latest_issue(FILE_WEILI)
    print(f"▶️ [威力彩] 目前 CSV 最新期數: {last_issue}")
    
    today_month = datetime.now().strftime("%Y-%m")
    url = f"https://api.taiwanlottery.com/TLCAPIWeB/Lottery/SuperLotto638Result?period&month={today_month}&pageNum=1&pageSize=50"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Origin': 'https://www.taiwanlottery.com',
        'Referer': 'https://www.taiwanlottery.com/'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        data = res.json()
        
        results = data.get("content", {}).get("superLotto638Res", [])
        if not results:
            print("❌ [威力彩] API 回傳無資料")
            return
            
        latest_draw = results[0]
        fetched_issue = str(latest_draw["period"])
        
        raw_date = latest_draw["lotteryDate"].split("T")[0]
        fetched_date = raw_date.replace("-", "/")
        
        nums = latest_draw["drawNumberSize"]
        second_sec = latest_draw.get("secondSection", "")
        
        nums_str = [str(n) for n in nums]
        if second_sec:
            nums_str.append(str(second_sec)) # 加入第二區號碼
            
        if int(fetched_issue) > int(last_issue):
            new_row = [fetched_issue, fetched_date] + nums_str
            
            with open(FILE_WEILI, 'a', newline='', encoding='big5', errors='ignore') as f:
                csv.writer(f).writerow(new_row)
            print(f"✅ [威力彩] 成功將第 {fetched_issue} 期真實號碼補進 CSV！")
        else:
            print("⏸️ [威力彩] 已是最新，無須更新。")
    except Exception as e:
        print(f"❌ [威力彩] 發生重大錯誤: {e}")

if __name__ == "__main__":
    fetch_539()
    print("-" * 30)
    fetch_weili()
