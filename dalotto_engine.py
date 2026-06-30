"""
dalotto_engine.py
大樂透預測引擎 — Cloud Run API 包裝版
供 api.py 呼叫 get_prediction(zodiac_id)
"""

import os
import pandas as pd
import numpy as np
from collections import Counter

# 引入本機引擎模組
from v7_engine import V7StructureEngine
from hit_engine import HitOptimizedEngine
from common_loader import normalize_csv, MAIN_COLS

CSV_NAME = "大樂透_歷史資料.csv"

# ── 載入 CSV ──────────────────────────────────────────────
def _load_csv():
    path = os.path.join(os.path.dirname(__file__), CSV_NAME)
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到 {CSV_NAME}")
    return normalize_csv(path)


def _load_539_csv():
    """嘗試載入539資料供CrossLotteryEngine使用，找不到就回傳None"""
    try:
        path = os.path.join(os.path.dirname(__file__), "今彩539_歷史資料.csv")
        if not os.path.exists(path):
            return None
        df = pd.read_csv(path, encoding="utf-8-sig")
        # 欄位對應
        col_map = {
            "期別": "period", "開獎日期": "date",
            "獎號1": "n1", "獎號2": "n2", "獎號3": "n3",
            "獎號4": "n4", "獎號5": "n5", "總和": "total"
        }
        df = df.rename(columns=col_map)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        for c in ["n1", "n2", "n3", "n4", "n5"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    except Exception:
        return None


# ── 主預測函式 ─────────────────────────────────────────────
def get_prediction(zodiac_id: int):
    try:
        df_lotto = _load_csv()
        df_539 = _load_539_csv()

        if len(df_lotto) < 20:
            return {"status": "error", "message": "大樂透歷史資料不足（需至少20期）"}

        target_idx = len(df_lotto)  # 預測最新下一期
        target_period = int(df_lotto.iloc[-1]["period"]) + 1

        # 建立引擎
        base_engine = HitOptimizedEngine(df_lotto)
        engine = V7StructureEngine(
            base_engine=base_engine,
            df_lotto=df_lotto,
            df_539=df_539,
        )

        # 產生12組預測（對應12生肖）
        _, _, _, combos = engine.generate(target_idx, sets=12)

        if not combos:
            return {"status": "error", "message": "大樂透引擎無法產生預測結果"}

        # 根據生肖id選取對應的那組號碼
        chosen_idx = (zodiac_id - 1) % len(combos)
        chosen = combos[chosen_idx]

        # 特別號預測
        special_candidates = []
        if hasattr(engine, "special_engine"):
            try:
                special_candidates = engine.special_engine.get_special_predictions(
                    target_idx, top_k=3
                )
            except Exception:
                special_candidates = []

        zone2 = int(special_candidates[0]) if special_candidates else None
        return {
            "status": "success",
            "type": "dalotto",
            "issue_number": str(target_period),
            "zone1": list(chosen.combo),
            "zone2": zone2,
            "special_candidates": special_candidates,
            "score": chosen.score,
        }

    except Exception as e:
        return {"status": "error", "message": f"大樂透引擎發生錯誤: {str(e)}"}


def get_backtest_detail(limit: int = 15) -> list:
    """
    真實 out-of-sample 回測：對最近 limit 期，各自用「該期之前的資料」預測，
    再與實際開獎比較，回傳每期每組生肖的命中數。
    邏輯完全對應 V7StructureEngine.backtest()。
    """
    df_lotto = _load_csv()
    df_539 = _load_539_csv()

    total_len = len(df_lotto)
    if total_len < 30:
        return []

    start_idx = max(30, total_len - limit)
    has_special = 'special' in df_lotto.columns

    base_engine = HitOptimizedEngine(df_lotto)
    engine = V7StructureEngine(base_engine=base_engine, df_lotto=df_lotto, df_539=df_539)

    results = []
    for target_idx in range(start_idx, total_len):
        row_data = df_lotto.iloc[target_idx]
        actual_nums = {
            int(float(row_data[f'n{i}']))
            for i in range(1, 7)
            if pd.notna(row_data.get(f'n{i}'))
        }
        actual_sp = (
            int(float(row_data['special']))
            if has_special and pd.notna(row_data.get('special'))
            else None
        )

        # generate() 使用 target_idx 前的資料做預測 — 同 V7StructureEngine.backtest()
        _, _, _, combos = engine.generate(target_idx, sets=12)

        zodiac_hits = []
        for i, c in enumerate(combos):
            zodiac_id = i + 1
            hit_main = len(set(c.combo) & actual_nums)
            has_sp = (actual_sp is not None) and (actual_sp in set(c.combo))
            hit_count = hit_main + (1 if has_sp else 0)
            zodiac_hits.append({
                'zodiac_id': zodiac_id,
                'hit_count': hit_count,
                'has_special': has_sp,
            })

        results.append({
            'draw_term': str(int(row_data['period'])),
            'draw_date': str(row_data.get('date', '')),
            'zodiac_hits': zodiac_hits,
        })

    return results


def get_all_predictions():
    """一次取得全部 12 組生肖預測，供回測比對用。返回 [(zone1_list, zone2_int_or_None)] * 12。"""
    try:
        df_lotto = _load_csv()
        df_539 = _load_539_csv()
        if len(df_lotto) < 20:
            return [([], None)] * 12
        target_idx = len(df_lotto)
        base_engine = HitOptimizedEngine(df_lotto)
        engine = V7StructureEngine(base_engine=base_engine, df_lotto=df_lotto, df_539=df_539)
        _, _, _, combos = engine.generate(target_idx, sets=12)
        special = None
        if hasattr(engine, "special_engine"):
            try:
                candidates = engine.special_engine.get_special_predictions(target_idx, top_k=1)
                special = int(candidates[0]) if candidates else None
            except Exception:
                pass
        n = len(combos)
        result = []
        for i in range(12):
            idx = i % n if n else 0
            zone1 = list(combos[idx].combo) if n else []
            result.append((zone1, special))
        return result
    except Exception:
        return [([], None)] * 12
