"""
每天由 GitHub Actions 在 crawler 之後執行。
預先計算三種彩券的 15 期回測，存成 JSON 檔，
Cloud Run 部署時會打包進 image，冷啟動直接讀檔案不需重算。
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(__file__)

import weili_v8_engine
import gichier539_engine
import dalotto_engine

_THRESHOLD = {'lotto': 2, 'power': 2, 'daily539': 2}
_ENGINES = {
    'lotto':    dalotto_engine,
    'power':    weili_v8_engine,
    'daily539': gichier539_engine,
}
LIMIT = 15

def compute(lottery_type: str) -> dict:
    engine = _ENGINES[lottery_type]
    threshold = _THRESHOLD[lottery_type]
    raw_detail = engine.get_backtest_detail(LIMIT)
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
    return {
        "status": "ok",
        "lottery_type": lottery_type,
        "threshold": threshold,
        "total_periods": len(results),
        "summary": {"max_hits_count": max_count, "max_hits_occurrences": occurrences},
        "data": results,
        "cached": False,
    }

errors = []
for lt in ('lotto', 'power', 'daily539'):
    print(f"[precompute] 計算 {lt} ...", flush=True)
    try:
        payload = compute(lt)
        path = os.path.join(BASE_DIR, f'{lt}_backtest_{LIMIT}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False)
        print(f"[precompute] {lt} OK → {path}", flush=True)
    except Exception as e:
        print(f"[precompute] {lt} FAILED: {e}", flush=True)
        errors.append(lt)

if errors:
    print(f"[precompute] 失敗項目: {errors}")
    sys.exit(1)

print("[precompute] 全部完成")
