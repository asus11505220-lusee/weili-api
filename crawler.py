import os
import csv

FILE_539 = '今彩539_歷史資料.csv'

def run_crawler():
    print("啟動機器人寫入測試...")
    
    # 故意捏造一筆假資料 (期數為 99999999)
    test_data = ['99999999', '2026/6/6', '01', '02', '03', '04', '05', '15']
    
    try:
        # 強制寫入 CSV 的最後一行
        with open(FILE_539, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(test_data)
        print("✅ 成功寫入一筆測試資料到 今彩539_歷史資料.csv！")
    except Exception as e:
        print(f"寫入發生錯誤: {e}")

if __name__ == "__main__":
    run_crawler()
