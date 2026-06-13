import os
import csv
import time
import requests
from datetime import datetime, timedelta

FILE_539 = '今彩539_歷史資料.csv'
FILE_WEILI = '威力彩_歷史資料.csv'

API_539 = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result"
API_WEILI = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/SuperLotto638Result"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.taiwanlottery.com/",
}

# 最多嘗試往後查幾期（避免無限迴圈；通常一天最多開1期，留點餘裕）
MAX_LOOKAHEAD = 5


def get_latest_issue(filename):
    """讀取CSV最後一筆的期數，回傳整數。檔案不存在或空白則回傳0"""
    if not os.path.exists(filename):
        return 0
    try:
        with open(filename, 'r', encoding='utf-8-sig', errors='ignore') as f:
            reader = list(csv.reader(f))
            valid_rows = [row for row in reader if row and str(row[0]).strip().isdigit()]
            if valid_rows:
                return int(str(valid_rows[-1][0]).strip())
    except Exception:
        pass
    return 0


def format_date(iso_date):
    """把 ISO 格式日期 (2026-06-12T00:00:00) 轉成 2026/06/12"""
    date_part = str(iso_date).split('T')[0]
    parts = date_part.split('-')
    if len(parts) == 3:
        return f"{parts[0]}/{parts[1].zfill(2)}/{parts[2].zfill(2)}"
    return str(iso_date)


def query_period(url, period):
    """查詢指定期數，回傳該期資料dict，查無資料回傳None"""
    try:
        resp = requests.get(
            url,
            params={"period": str(period)},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"⚠️ 查詢第{period}期時發生錯誤: {e}")
        return None

    if data.get("rtCode") != 0:
        return None

    content = data.get("content") or {}
    res_list = content.get("daily539Res") or content.get("superLotto638Res")
    if not res_list:
        return None

    # 取第一筆即為該期資料
    return res_list[0]


def fetch_539():
    last_issue = get_latest_issue(FILE_539)
    print(f"📌 [今彩539] 目前CSV最後一期：{last_issue}")

    found = False
    for offset in range(1, MAX_LOOKAHEAD + 1):
        next_issue = last_issue + offset
        item = query_period(API_539, next_issue)
        if not item:
            # 查無資料：代表這期還沒開獎，停止往後查
            break

        date = format_date(item.get("lotteryDate", ""))
        nums = item.get("drawNumberSize") or []
        nums = [str(n).zfill(2) for n in nums][:5]
        if len(nums) != 5:
            print(f"⚠️ [今彩539] 第{next_issue}期號碼數量異常，略過: {nums}")
            continue

        total_sum = str(sum(int(n) for n in nums))
        row = [str(next_issue), date] + nums + [total_sum]

        with open(FILE_539, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(row)
        print(f"✅ 成功補進 今彩539 第 {next_issue} 期 ({date}): {nums}")
        found = True
        time.sleep(0.5)

    if not found:
        print("⏸️ [今彩539] 目前已是最新。")


def fetch_weili():
    last_issue = get_latest_issue(FILE_WEILI)
    print(f"📌 [威力彩] 目前CSV最後一期：{last_issue}")

    found = False
    for offset in range(1, MAX_LOOKAHEAD + 1):
        next_issue = last_issue + offset
        item = query_period(API_WEILI, next_issue)
        if not item:
            break

        date = format_date(item.get("lotteryDate", ""))
        size_arr = item.get("drawNumberSize") or []
        # drawNumberSize 共7個數字：前6個為第一區(已排序)，第7個為第二區
        if len(size_arr) != 7:
            print(f"⚠️ [威力彩] 第{next_issue}期號碼數量異常，略過: {size_arr}")
            continue
        nums = [str(n).zfill(2) for n in size_arr[:6]]
        second_area = str(size_arr[6]).zfill(2)
        row = [str(next_issue), date] + nums + [second_area]

        with open(FILE_WEILI, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(row)
        print(f"✅ 成功補進 威力彩 第 {next_issue} 期 ({date}): {nums} + 第二區 {second_area}")
        found = True
        time.sleep(0.5)

    if not found:
        print("⏸️ [威力彩] 目前已是最新。")


if __name__ == "__main__":
    print("🚀 啟動台彩官方API爬取模式 (period 逐期查詢)...")
    fetch_539()
    fetch_weili()
