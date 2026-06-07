import os
import csv
import requests
from bs4 import BeautifulSoup
import re

FILE_539 = '今彩539_歷史資料.csv'
FILE_WEILI = '威力彩_歷史資料.csv'

def get_latest_issue(filename):
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

def fetch_pilio_539():
    last_issue = get_latest_issue(FILE_539)
    print(f"▶️ [今彩539] 目前 CSV 最新期數: {last_issue}")
    
    # 🌟 改抓不擋 GitHub 的第三方網站：樂透研究院
    url = "https://www.pilio.idv.tw/lto539/list.asp"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        found_new = False
        
        # 掃描網頁中的所有表格行 (從上到下，最新的在上面)
        # 我們將網頁內容反轉讀取，確保歷史資料依序寫入
        rows = soup.find_all('tr')
        for tr in reversed(rows):
            text_content = tr.get_text(separator=' ', strip=True)
            
            # 🔥 暴力解析法：精準找尋 9碼期數 + 日期 + 5個兩位數
            match = re.search(r'(\d{9}).*?(\d{4}[-/]\d{1,2}[-/]\d{1,2}).*?(?<!\d)(\d{2})\D+(\d{2})\D+(\d{2})\D+(\d{2})\D+(\d{2})(?!\d)', text_content)
            
            if match:
                fetched_issue = match.group(1)
                fetched_date = match.group(2).replace('-', '/')
                nums = [match.group(3), match.group(4), match.group(5), match.group(6), match.group(7)]
                
                # 比對期數，大於我們最後一期的才寫入
                if int(fetched_issue) > int(last_issue):
                    total_sum = sum(int(n) for n in nums)
                    new_row = [fetched_issue, fetched_date] + nums + [str(total_sum)]
                    
                    with open(FILE_539, 'a', newline='', encoding='big5', errors='ignore') as f:
                        csv.writer(f).writerow(new_row)
                    print(f"✅ [今彩539] 成功補進第 {fetched_issue} 期！號碼: {nums}")
                    last_issue = fetched_issue  # 更新最新期數
                    found_new = True
                    
        if not found_new:
            print("⏸️ [今彩539] 已經是最新的了，沒有新資料。")

    except Exception as e:
        print(f"❌ [今彩539] 爬蟲失敗: {e}")

def fetch_pilio_weili():
    last_issue = get_latest_issue(FILE_WEILI)
    print(f"▶️ [威力彩] 目前 CSV 最新期數: {last_issue}")
    
    url = "https://www.pilio.idv.tw/ltobig/list.asp"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        found_new = False
        
        rows = soup.find_all('tr')
        for tr in reversed(rows):
            text_content = tr.get_text(separator=' ', strip=True)
            
            # 🔥 威力彩：9碼期數 + 日期 + 6個第一區號碼 + 1個第二區號碼 (總共7個號碼)
            match = re.search(r'(\d{9}).*?(\d{4}[-/]\d{1,2}[-/]\d{1,2}).*?(?<!\d)(\d{2})\D+(\d{2})\D+(\d{2})\D+(\d{2})\D+(\d{2})\D+(\d{2})\D+(\d{2})(?!\d)', text_content)
            
            if match:
                fetched_issue = match.group(1)
                fetched_date = match.group(2).replace('-', '/')
                nums = [match.group(3), match.group(4), match.group(5), match.group(6), match.group(7), match.group(8), match.group(9)]
                
                if int(fetched_issue) > int(last_issue):
                    new_row = [fetched_issue, fetched_date] + nums
                    
                    with open(FILE_WEILI, 'a', newline='', encoding='big5', errors='ignore') as f:
                        csv.writer(f).writerow(new_row)
                    print(f"✅ [威力彩] 成功補進第 {fetched_issue} 期！號碼: {nums}")
                    last_issue = fetched_issue
                    found_new = True
                    
        if not found_new:
            print("⏸️ [威力彩] 已經是最新的了，沒有新資料。")

    except Exception as e:
        print(f"❌ [威力彩] 爬蟲失敗: {e}")

if __name__ == "__main__":
    fetch_pilio_539()
    print("-" * 30)
    fetch_pilio_weili()
