import os, glob
import pandas as pd

RAW_MAP = {'期別':'period','開獎日期':'date','獎號1':'n1','獎號2':'n2','獎號3':'n3','獎號4':'n4','獎號5':'n5','獎號6':'n6','特別號':'special'}
STD_COLS = ['period','date','n1','n2','n3','n4','n5','n6','special']
MAIN_COLS = ['n1','n2','n3','n4','n5','n6']

def normalize_csv(path):
    last_err = None
    for enc in ['utf-8-sig','cp950','utf-8']:
        try:
            df = pd.read_csv(path, encoding=enc)
            if set(STD_COLS).issubset(df.columns):
                out = df[STD_COLS].copy()
            elif set(RAW_MAP.keys()).issubset(df.columns):
                out = df[list(RAW_MAP.keys())].rename(columns=RAW_MAP).copy()
            else:
                raise ValueError(f'欄位不支援: {list(df.columns)}')
            out['period'] = out['period'].astype(int)
            for c in MAIN_COLS + ['special']:
                out[c] = out[c].astype(int)
            return out
        except Exception as e:
            last_err = e
    raise last_err

def load_history(paths):
    files = []
    for p in paths:
        found = glob.glob(os.path.join(p, "*.csv"))
        # 排除539資料，只載入大樂透
        found = [f for f in found if "539" not in os.path.basename(f)]
        files += found
    if not files:
        raise FileNotFoundError("找不到大樂透歷史CSV！\n請確認 .csv 檔案與 dalotto_v7.py 放在同一資料夾。")
    dfs = []
    for f in files:
        try:
            dfs.append(normalize_csv(f))
        except Exception as e:
            print(f"⚠️  跳過 {os.path.basename(f)}：{e}")
    if not dfs:
        raise FileNotFoundError("找到CSV但無法解析，請確認欄位格式。")
    df = pd.concat(dfs).drop_duplicates("period").sort_values("period").reset_index(drop=True)
    return df, files
