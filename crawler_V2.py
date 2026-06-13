import os
import csv
import requests

FILE_539 = '今彩539_歷史資料.csv'
FILE_WEILI = '威力彩_歷史資料.csv'

# 台彩官方開獎 API
API_539 = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/Daily539Result"
API_WEILI = "https://api.taiwanlottery.com/TLCAPIWeB/Lottery/SuperLotto638Result"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


def get_latest_issue(filename):
    """讀取CSV最後一筆的期數，回傳字串。檔案不存在或空白則回傳'0'"""
    if not os.path.exists(filename):
        return "0"
    try:
        with open(filename, 'r', encoding='utf-8-sig', errors='ignore') as f:
            reader = list(csv.reader(f))
            valid_rows = [row for row in reader if len(row) > 0]
            if len(valid_rows) >= 1:
                return str(valid_rows[-1][0]).strip()
    except Exception:
        pass
    return "0"


def format_date(raw_date):
    """把 ISO 格式日期 (2026-06-12T00:00:00) 轉成 2026/06/12"""
    date_part = raw_date.split('T')[0]
    parts = date_part.split('-')
    if len(parts) == 3:
        return f"{parts[0]}/{parts[1].zfill(2)}/{parts[2].zfill(2)}"
    return raw_date


def fetch_539():
    last_issue = get_latest_issue(FILE_539)
    print(f"📌 [今彩539] 目前CSV最後一期：{last_issue}")

    try:
        resp = requests.get(
            API_539,
            params={"period": "", "pageNum": 1, "pageSize": 10},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ [今彩539] API 請求失敗: {e}")
        return

    # 官方API回傳結構: data['content']['result'] 為清單，最新一期在最前面
    try:
        results = data.get("content", {}).get("result", [])
    except Exception:
        results = []

    if not results:
        print("❌ [今彩539] API 回傳資料格式異常或為空")
        return

    # 由舊到新排序，逐一檢查是否要新增
    results = sorted(results, key=lambda r: int(r.get("period", 0)))

    found = False
    for item in results:
        issue = str(item.get("period", "")).strip()
        if not issue.isdigit():
            continue
        if int(issue) > int(last_issue):
            date = format_date(item.get("lotteryDate", ""))
            nums = item.get("drawNumberAppear") or item.get("drawNumberSize") or []
            nums = [str(n).zfill(2) for n in nums][:5]
            if len(nums) != 5:
                print(f"⚠️ [今彩539] 第{issue}期號碼數量異常，略過: {nums}")
                continue
            total_sum = str(sum(int(n) for n in nums))
            row = [issue, date] + nums + [total_sum]

            with open(FILE_539, 'a', newline='', encoding='utf-8-sig') as f:
                csv.writer(f).writerow(row)
            print(f"✅ 成功補進 今彩539 第 {issue} 期 ({date}): {nums}")
            last_issue = issue
            found = True

    if not found:
        print("⏸️ [今彩539] 目前已是最新。")


def fetch_weili():
    last_issue = get_latest_issue(FILE_WEILI)
    print(f"📌 [威力彩] 目前CSV最後一期：{last_issue}")

    try:
        resp = requests.get(
            API_WEILI,
            params={"period": "", "pageNum": 1, "pageSize": 10},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ [威力彩] API 請求失敗: {e}")
        return

    try:
        results = data.get("content", {}).get("result", [])
    except Exception:
        results = []

    if not results:
        print("❌ [威力彩] API 回傳資料格式異常或為空")
        return

    results = sorted(results, key=lambda r: int(r.get("period", 0)))

    found = False
    for item in results:
        issue = str(item.get("period", "")).strip()
        if not issue.isdigit():
            continue
        if int(issue) > int(last_issue):
            date = format_date(item.get("lotteryDate", ""))
            nums = item.get("drawNumberAppear") or item.get("drawNumberSize") or []
            nums = [str(n).zfill(2) for n in nums][:6]
            second_area = item.get("secondAreaNumber") or item.get("specialNumber")
            if len(nums) != 6 or second_area is None:
                print(f"⚠️ [威力彩] 第{issue}期號碼數量異常，略過: {nums} / {second_area}")
                continue
            second_area = str(second_area).zfill(2)
            row = [issue, date] + nums + [second_area]

            with open(FILE_WEILI, 'a', newline='', encoding='utf-8-sig') as f:
                csv.writer(f).writerow(row)
            print(f"✅ 成功補進 威力彩 第 {issue} 期 ({date}): {nums} + 第二區 {second_area}")
            last_issue = issue
            found = True

    if not found:
        print("⏸️ [威力彩] 目前已是最新。")


if __name__ == "__main__":
    print("🚀 啟動台彩官方API爬取模式...")
    fetch_539()
    fetch_weili()
