import os
import csv
import time
import requests

FILE_539   = '今彩539_歷史資料.csv'
FILE_WEILI = '威力彩_歷史資料.csv'
FILE_LOTTO = '大樂透_歷史資料.csv'

API_539   = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result"
API_WEILI = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/SuperLotto638Result"
API_LOTTO = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/LottoResult"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.taiwanlottery.com/",
}

MAX_LOOKAHEAD = 5


def get_latest_issue(filename):
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
    date_part = str(iso_date).split('T')[0]
    parts = date_part.split('-')
    if len(parts) == 3:
        return f"{parts[0]}/{parts[1].zfill(2)}/{parts[2].zfill(2)}"
    return str(iso_date)


def query_period(url, period, res_key=None):
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
    # 自動偵測回傳的資料key
    if res_key:
        res_list = content.get(res_key)
    else:
        res_list = (content.get("daily539Res") or
                    content.get("superLotto638Res") or
                    content.get("bigLottoRes") or
                    content.get("lotto649Res"))
    if not res_list:
        return None
    return res_list[0]


def fetch_539():
    last_issue = get_latest_issue(FILE_539)
    print(f"📌 [今彩539] 目前CSV最後一期：{last_issue}")
    found = False
    for offset in range(1, MAX_LOOKAHEAD + 1):
        next_issue = last_issue + offset
        item = query_period(API_539, next_issue)
        if not item:
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


def fetch_lotto():
    last_issue = get_latest_issue(FILE_LOTTO)
    print(f"📌 [大樂透] 目前CSV最後一期：{last_issue}")
    found = False
    for offset in range(1, MAX_LOOKAHEAD + 1):
        next_issue = last_issue + offset
        item = query_period(API_LOTTO, next_issue)
        if not item:
            break
        date = format_date(item.get("lotteryDate", ""))
        size_arr = item.get("drawNumberSize") or []
        special = item.get("specialNo") or item.get("bonusNum") or item.get("drawNumberBonus")
        if len(size_arr) < 6 or special is None:
            print(f"⚠️ [大樂透] 第{next_issue}期號碼異常，略過: nums={size_arr}, special={special}")
            print(f"   原始item keys: {list(item.keys())}")
            continue
        nums = [str(n).zfill(2) for n in size_arr[:6]]
        special_str = str(special).zfill(2)
        row = [str(next_issue), date] + nums + [special_str]
        with open(FILE_LOTTO, 'a', newline='', encoding='utf-8-sig') as f:
            csv.writer(f).writerow(row)
        print(f"✅ 成功補進 大樂透 第 {next_issue} 期 ({date}): {nums} + 特別號 {special_str}")
        found = True
        time.sleep(0.5)
    if not found:
        print("⏸️ [大樂透] 目前已是最新。")


if __name__ == "__main__":
    print("🚀 啟動台彩官方API爬取模式 (period 逐期查詢)...")
    fetch_539()
    fetch_weili()
    fetch_lotto()
