from fastapi import FastAPI, HTTPException, Security, Query
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import os
import time
import pandas as pd

import weili_v8_engine
import gichier539_engine
import dalotto_engine

# ── 回測結果記憶體快取（避免每次請求重跑耗時引擎）─────────────────
_backtest_cache: dict = {}   # key: (lottery_type, limit) → (timestamp, payload)
_CACHE_TTL = 3600            # 1 小時後過期，重新計算

app = FastAPI(title="生肖威力今彩大樂透 API (加密防護版)")

API_KEY = "Fortune2026-SuperKey"
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def check_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="🔒 密鑰錯誤或未授權，拒絕惡意連線！")

@app.get("/generate")
def generate_weili(zodiac_id: int = 1, api_key: str = Security(check_api_key)):
    return weili_v8_engine.get_prediction(zodiac_id)

@app.get("/generate_539")
def generate_539(zodiac_id: int = 1, api_key: str = Security(check_api_key)):
    return gichier539_engine.get_prediction(zodiac_id)

@app.get("/generate_lotto")
def generate_lotto(zodiac_id: int = 1, api_key: str = Security(check_api_key)):
    return dalotto_engine.get_prediction(zodiac_id)


# ── 生肖對照表 ─────────────────────────────────────────────────
_ZODIAC_LIST = [
    (1, '鼠', '🐀'), (2, '牛', '🐂'), (3, '虎', '🐅'), (4, '兔', '🐇'),
    (5, '龍', '🐉'), (6, '蛇', '🐍'), (7, '馬', '🐎'), (8, '羊', '🐑'),
    (9, '猴', '🐒'), (10, '雞', '🐓'), (11, '狗', '🐕'), (12, '豬', '🐖'),
]

_BASE_DIR = os.path.dirname(__file__)

# ── CSV 設定 ───────────────────────────────────────────────────
_LOTTERY_CFG = {
    'lotto':    ('大樂透_歷史資料.csv', ['n1','n2','n3','n4','n5','n6'], 'special'),
    'power':    ('威力彩_歷史資料.csv', ['n1','n2','n3','n4','n5','n6'], 'special'),
    'daily539': ('今彩539_歷史資料.csv', ['n1','n2','n3','n4','n5'],     None),
}

# 每個彩券類型的命中門檻（含特別號/第二區）
_LOTTERY_THRESHOLD = {'lotto': 3, 'power': 2, 'daily539': 2}

# 欄位名稱對應表，涵蓋大樂透、威力彩、今彩539 的各種標頭寫法
_COL_RENAME = {
    '期別': 'period', '期次': 'period', '期號': 'period',
    '開獎日期': 'date', '日期': 'date',
    '獎號1': 'n1', '第一區1': 'n1', '號碼1': 'n1',
    '獎號2': 'n2', '第一區2': 'n2', '號碼2': 'n2',
    '獎號3': 'n3', '第一區3': 'n3', '號碼3': 'n3',
    '獎號4': 'n4', '第一區4': 'n4', '號碼4': 'n4',
    '獎號5': 'n5', '第一區5': 'n5', '號碼5': 'n5',
    '獎號6': 'n6', '第一區6': 'n6', '號碼6': 'n6',
    '特別號': 'special', '第二區': 'special', '第二區號碼': 'special',
}


def _load_df(lottery_type: str) -> pd.DataFrame:
    cfg = _LOTTERY_CFG.get(lottery_type)
    if not cfg:
        raise ValueError(f"不支援的彩券類型: {lottery_type}")
    csv_name, num_cols, special_col = cfg
    has_special = special_col is not None
    path = os.path.join(_BASE_DIR, csv_name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到 {csv_name}")

    for enc in ('utf-8-sig', 'cp950', 'big5', 'utf-8'):
        try:
            df = pd.read_csv(path, encoding=enc)
            # 去除欄位名稱的 BOM 殘留與空白
            df.columns = [str(c).lstrip('﻿').strip() for c in df.columns]
            df = df.rename(columns=_COL_RENAME)

            # 位置式後備：若 header-based 對應失敗，按欄位順序強制命名
            if 'period' not in df.columns:
                raw = df.columns.tolist()
                pos_names = ['period', 'date'] + num_cols + (['special'] if has_special else [])
                if len(raw) >= len(pos_names):
                    df = df.rename(columns={raw[i]: pos_names[i] for i in range(len(pos_names))})

            if 'period' not in df.columns:
                continue

            df['period'] = pd.to_numeric(df['period'], errors='coerce')
            for c in num_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce')
            if has_special and 'special' in df.columns:
                df['special'] = pd.to_numeric(df['special'], errors='coerce')

            result = df.dropna(subset=['period']).sort_values('period').reset_index(drop=True)
            if not result.empty:
                return result
        except Exception:
            continue

    raise RuntimeError(f"無法解析 {csv_name}")


# ── 生肖幸運號計算 ─────────────────────────────────────────────

def _get_all_predictions(lottery_type: str) -> list:
    """呼叫對應引擎，一次取得全部 12 組預測。返回 [(zone1_list, zone2_or_None)] * 12。"""
    try:
        if lottery_type == 'lotto':
            return dalotto_engine.get_all_predictions()
        elif lottery_type == 'power':
            return weili_v8_engine.get_all_predictions()
        elif lottery_type == 'daily539':
            return gichier539_engine.get_all_predictions()
    except Exception:
        pass
    return [([], None)] * 12


def _calc_period_zodiac_hits(numbers: list, special, predictions: list, lottery_type: str) -> list:
    """以引擎實際預測號碼比對歷史開獎，計算每組生肖的命中數。"""
    actual_main = set(numbers)
    results = []
    for i, (pred_zone1, pred_zone2) in enumerate(predictions):
        zodiac_id = i + 1
        pred_set = set(pred_zone1)
        if lottery_type == 'lotto':
            hit_main = len(pred_set & actual_main)
            has_sp = (special is not None) and (special in pred_set)
            hit_count = hit_main + (1 if has_sp else 0)
        elif lottery_type == 'power':
            hit_main = len(pred_set & actual_main)
            has_sp = (special is not None) and (pred_zone2 is not None) and (pred_zone2 == special)
            hit_count = hit_main + (1 if has_sp else 0)
        else:  # daily539
            hit_count = len(pred_set & actual_main)
            has_sp = False
        results.append({'zodiac_id': zodiac_id, 'hit_count': hit_count, 'has_special': has_sp})
    return results


# ── /api/v1/lotto/latest ──────────────────────────────────────
@app.get("/api/v1/lotto/latest")
def latest_lotto():
    try:
        df = _load_df('lotto')
        if df.empty:
            return {"status": "error", "error_message": "無大樂透歷史資料",
                    "draw_date": "", "draw_term": "", "numbers": [], "special_number": None, "cached": False}
        row = df.iloc[-1]
        numbers = [int(row[c]) for c in ['n1','n2','n3','n4','n5','n6'] if c in row and pd.notna(row[c])]
        special = int(row['special']) if 'special' in row.index and pd.notna(row['special']) else None
        return {
            "status": "ok",
            "draw_term": str(int(row['period'])),
            "draw_date": str(row.get('date', '')),
            "numbers": numbers,
            "special_number": special,
            "cached": False,
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e),
                "draw_date": "", "draw_term": "", "numbers": [], "special_number": None, "cached": False}


# ── /api/v1/backtest ─────────────────────────────────────────
@app.get("/api/v1/backtest")
def backtest(lottery_type: str = Query('lotto', alias='type'), limit: int = Query(15)):
    threshold = _LOTTERY_THRESHOLD.get(lottery_type, 2)
    try:
        cfg = _LOTTERY_CFG.get(lottery_type)
        if not cfg:
            raise ValueError(f"不支援的彩券類型: {lottery_type}")

        # 快取命中：直接回傳已計算結果
        cache_key = (lottery_type, limit)
        cached = _backtest_cache.get(cache_key)
        if cached:
            ts, payload = cached
            if time.time() - ts < _CACHE_TTL:
                payload['cached'] = True
                return payload

        _, num_cols, special_col = cfg
        df = _load_df(lottery_type)
        if df.empty:
            return {
                "status": "error", "error_message": "無歷史資料",
                "lottery_type": lottery_type, "threshold": threshold,
                "total_periods": 0,
                "summary": {"max_hits_count": 0, "max_hits_occurrences": 0},
                "data": [], "cached": False,
            }

        # 大樂透：使用引擎內建的 out-of-sample 回測（每期用截止前的資料預測）
        if lottery_type == 'lotto':
            raw_detail = dalotto_engine.get_backtest_detail(limit)
            results = []
            all_hit_counts = []
            for entry in raw_detail:
                all_hits = entry['zodiac_hits']
                all_hit_counts.extend(h['hit_count'] for h in all_hits if h['hit_count'] > 0)
                qualifying = [h for h in all_hits if h['hit_count'] >= threshold]
                results.append({
                    "draw_term":   entry['draw_term'],
                    "draw_date":   entry['draw_date'],
                    "zodiac_hits": qualifying,
                })
        elif lottery_type == 'power':
            # 威力彩：使用引擎內建的 out-of-sample 回測
            raw_detail = weili_v8_engine.get_backtest_detail(limit)
            results = []
            all_hit_counts = []
            for entry in raw_detail:
                all_hits = entry['zodiac_hits']
                all_hit_counts.extend(h['hit_count'] for h in all_hits if h['hit_count'] > 0)
                qualifying = [h for h in all_hits if h['hit_count'] >= threshold]
                results.append({
                    "draw_term":   entry['draw_term'],
                    "draw_date":   entry['draw_date'],
                    "zodiac_hits": qualifying,
                })
        else:
            # 今彩539：使用引擎內建的 out-of-sample 回測
            raw_detail = gichier539_engine.get_backtest_detail(limit)
            results = []
            all_hit_counts = []
            for entry in raw_detail:
                all_hits = entry['zodiac_hits']
                all_hit_counts.extend(h['hit_count'] for h in all_hits if h['hit_count'] > 0)
                qualifying = [h for h in all_hits if h['hit_count'] >= threshold]
                results.append({
                    "draw_term":   entry['draw_term'],
                    "draw_date":   entry['draw_date'],
                    "zodiac_hits": qualifying,
                })

        max_count = max(all_hit_counts) if all_hit_counts else 0
        occurrences = all_hit_counts.count(max_count) if max_count > 0 else 0

        payload = {
            "status": "ok",
            "lottery_type": lottery_type,
            "threshold": threshold,
            "total_periods": len(results),
            "summary": {"max_hits_count": max_count, "max_hits_occurrences": occurrences},
            "data": results,
            "cached": False,
        }
        _backtest_cache[cache_key] = (time.time(), payload)
        return payload
    except Exception as e:
        return {
            "status": "error", "error_message": str(e),
            "lottery_type": lottery_type, "threshold": threshold,
            "total_periods": 0,
            "summary": {"max_hits_count": 0, "max_hits_occurrences": 0},
            "data": [], "cached": False,
        }
