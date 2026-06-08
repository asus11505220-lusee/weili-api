import os
import csv
import re
import cloudscraper
from bs4 import BeautifulSoup

FILE_539 = '今彩539_歷史資料.csv'
FILE_WEILI = '威力彩_歷史資料.csv'

def get_latest_issue(filename):
    if not os.path.exists(filename): return "0"
    try:
        with open(filename, 'r', encoding='big5', errors='ignore') as f:
            reader = list(csv.reader(f))
            valid_rows = [row for row in reader if len(row) > 0]
            if len(valid_rows) > 1: return str(valid_rows[-1][0]).strip()
    except Exception: pass
    return "0"

def format_date(raw_date):
    # 確保日期格式永遠是 2026/06/06，符合你的自創 CSV 格式
    parts = raw_date.replace('-', '/').split('/')
    if len(parts) == 3:
        return f"{parts[0]}/{parts[1].zfill(2)}/{parts[2].zfill(2)}"
    return raw_date

def fetch_from_pilio():
    # 使用 cloudscraper 完美繞過網站防火牆
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    
    # ==========================================
    # 1. 處理今彩 539 (抓取你的截圖網址)
    # ==========================================
    last_issue_539 = get_latest_issue(FILE_539)
    try:
        res = scraper.get("https://www.pilio.idv.tw/lto539/list.asp", timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 把網頁全部轉成純文字，不看 HTML 標籤
        text = soup.get_text(separator=' ')
        
        # 用正則表達式尋找：9碼期數 + 日期 + 5個號碼
        matches = re.findall(r'(\d{9})\s+(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})(?!\d)', text)
        matches.reverse() # 從舊排到新
        
        found_539 = False
        for match in matches:
            issue = match[0]
            if int(issue) > int(last_issue_539):
                date = format_date(match[1])
                nums = list(match[2:7])
                total_sum = str(sum(int(n) for n in nums))
                
                # 組合出你自創的格式：[期數, 日期, 球1, 球2, 球3, 球4, 球5, 總和]
                row = [issue, date] + nums + [total_sum]
                
                with open(FILE_539, 'a', newline='', encoding='big5', errors='ignore') as f:
                    csv.writer(f).writerow(row)
                print(f"✅ 成功補進 今彩539 第 {issue} 期")
                last_issue_539 = issue
                found_539 = True
                
        if not found_539: print("⏸️ [今彩539] 目前已是最新。")
    except Exception as e:
        print(f"❌ [今彩539] 網頁解析失敗: {e}")

    # ==========================================
    # 2. 處理威力彩 (抓取你的截圖網址)
    # ==========================================
    last_issue_weili = get_latest_issue(FILE_WEILI)
    try:
        res = scraper.get("https://www.pilio.idv.tw/ltowei/list.asp", timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text(separator=' ')
        
        # 用正則表達式尋找：9碼期數 + 日期 + 7個號碼 (第一區6個 + 第二區1個)
        matches = re.findall(r'(\d{9})\s+(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})\s+(\d{2})(?!\d)', text)
        matches.reverse()
        
        found_weili = False
        for match in matches:
            issue = match[0]
            if int(issue) > int(last_issue_weili):
                date = format_date(match[1])
                nums = list(match[2:9])
                
                # 組合出你自創的格式：[期數, 日期, 球1, 球2, 球3, 球4, 球5, 球6, 第二區]
                row = [issue, date] + nums
                
                with open(FILE_WEILI, 'a', newline='', encoding='big5', errors='ignore') as f:
                    csv.writer(f).writerow(row)
                print(f"✅ 成功補進 威力彩 第 {issue} 期")
                last_issue_weili = issue
                found_weili = True
                
        if not found_weili: print("⏸️ [威力彩] 目前已是最新。")
    except Exception as e:
        print(f"❌ [威力彩] 網頁解析失敗: {e}")

if __name__ == "__main__":
    print("🚀 啟動網頁直接解析模式 (直連樂透研究院)...")
    fetch_from_pilio()