import csv
import os
import math
import random
import itertools
from itertools import combinations
from collections import Counter
import copy
import sys

CSV_NAME = '今彩539_歷史資料.csv'
ENCODINGS = ['utf-8-sig', 'cp950', 'big5', 'utf-8']
TOP_POOL = 30  
MAX_COMBOS = 12
BACKTEST_LOOKBACK = 54

COLORS = [
    '\033[41;97m',  # 紅底白字
    '\033[42;97m',  # 綠底白字
    '\033[43;30m',  # 黃底黑字
    '\033[44;97m',  # 藍底白字
    '\033[45;97m',  # 紫底白字
    '\033[46;30m',  # 青底黑字
    '\033[101;97m', # 亮紅底白字
    '\033[102;30m', # 亮綠底黑字
    '\033[103;30m', # 亮黃底黑字
    '\033[104;97m', # 亮藍底白字
    '\033[105;97m', # 亮紫底白字
    '\033[106;30m', # 亮青底黑字
]
RESET_COLOR = '\033[0m'

def load_csv(filename):
    import io
    import csv
    ENCODINGS = ['utf-8-sig', 'cp950', 'big5', 'utf-8']
    last_err = None
    for enc in ENCODINGS:
        try:
            with open(filename, 'rb') as f:
                raw = f.read()
            text = raw.decode(enc, errors='replace')
            reader = csv.reader(io.StringIO(text))
            all_rows = list(reader)
            if len(all_rows) < 2:
                continue
            normalized = []
            for row in all_rows[1:]:  # 跳過第一行標頭
                try:
                    if len(row) < 7:
                        continue
                    period = str(row[0]).strip()
                    date = str(row[1]).strip()
                    nums = []
                    for i in range(2, 7):  # 欄位2~6是獎號1~5
                        val = str(row[i]).strip()
                        if val.isdigit():
                            nums.append(int(val))
                    if period and date and len(nums) == 5:
                        normalized.append({
                            'draw': int(period),
                            'date': date,
                            'nums': sorted(nums)
                        })
                except Exception:
                    continue
            if normalized:
                normalized.sort(key=lambda x: x['draw'])
                return normalized, enc
        except Exception as e:
            last_err = e
    return [], None  # 找不到資料時安全回傳空值，不讓伺服器當機

def missing_span(n, history):
    for i, row in enumerate(reversed(history), 1):
        if n in row['nums']: return i - 1
    return len(history)

def build_transition_matrix(history, limit=200):
    rows = history[-limit:] if len(history) >= limit else history[:]
    transition = Counter()
    for i in range(len(rows) - 1):
        cur = rows[i]['nums']
        nxt = rows[i + 1]['nums']
        for a in cur:
            for b in nxt: transition[(a, b)] += 1
    return transition

def build_pair_stats(history, limit=150):
    rows = history[-limit:] if len(history) >= limit else history[:]
    pair_count = Counter()
    for row in rows:
        for a, b in combinations(row['nums'], 2): pair_count[tuple(sorted((a, b)))] += 1
    return pair_count

def build_triplet_stats(history, limit=200):
    rows = history[-limit:] if len(history) >= limit else history[:]
    triplet_count = Counter()
    for row in rows:
        for tri in combinations(row['nums'], 3): triplet_count[tuple(sorted(tri))] += 1
    return triplet_count

def score_number_v82(n, history, transition_matrix):
    l5  = history[-5:]  if len(history) >= 5  else history[:]
    l10 = history[-10:] if len(history) >= 10 else history[:]
    l20 = history[-20:] if len(history) >= 20 else history[:]
    l30 = history[-30:] if len(history) >= 30 else history[:]
    l40 = history[-40:] if len(history) >= 40 else history[:]
    l50 = history[-50:] if len(history) >= 50 else history[:]
    prev_draw = history[-1]['nums'] if history else []

    c5  = sum(1 for r in l5  if n in r['nums'])
    c10 = sum(1 for r in l10 if n in r['nums'])
    c20 = sum(1 for r in l20 if n in r['nums'])
    c30 = sum(1 for r in l30 if n in r['nums'])
    c40 = sum(1 for r in l40 if n in r['nums'])
    c50 = sum(1 for r in l50 if n in r['nums'])
    
    miss = missing_span(n, history)
    score = 0.0
    reasons = []

    if c5 >= 2: score += 2.5; reasons.append(f'5MA爆發({c5})')
    elif c5 == 1: score += 1.0; reasons.append(f'5MA活躍')
    if c10 >= 3: score += 2.0; reasons.append(f'10MA走強({c10})')
    elif c10 == 2: score += 1.0; reasons.append(f'10MA溫和')
    if c20 >= 5: score += 1.5; reasons.append(f'20MA多頭({c20})')
    if c30 >= 7: score += 1.0; reasons.append(f'30MA支撐({c30})')
    if c40 >= 9: score += 1.0; reasons.append(f'40MA穩健({c40})')
    if c50 >= 11: score += 1.0; reasons.append(f'50MA長多({c50})')

    trans_hits = sum(transition_matrix.get((p, n), 0) for p in prev_draw)
    if trans_hits > 0:
        score += min(3.0, trans_hits * 0.3)
        if trans_hits >= 5: reasons.append(f'強拖牌({trans_hits})')

    if miss >= 15:
        score += 2.5; reasons.append(f'大冷回補(漏{miss})') 
    elif miss == 1:
        score += 1.2; reasons.append('單跳慣性')

    return round(score, 2), reasons, {'miss': miss}

def build_pool_v82(history):
    transition_matrix = build_transition_matrix(history)
    pair_stats_long = build_pair_stats(history, limit=150)
    triplet_stats_long = build_triplet_stats(history, limit=200) 
    
    scored = []
    for n in range(1, 40):
        sc, reasons, meta = score_number_v82(n, history, transition_matrix)
        scored.append({'num': n, 'score': sc, 'reasons': reasons, 'meta': meta})
        
    scored.sort(key=lambda x: -x['score'])
    top_24 = scored[:24]
    remaining = scored[24:]
    remaining.sort(key=lambda x: -x['meta']['miss'])
    cold_6 = remaining[:6]
    for c in cold_6:
        if not c['reasons']: c['reasons'].append(f"絕對零度(漏{c['meta']['miss']}期)")
        
    final_pool = top_24 + cold_6
    return final_pool, pair_stats_long, triplet_stats_long

def combo_bucket_bonus_v82(combo, row_map):
    bonus = 0.0
    flat_reasons = '、'.join('、'.join(row_map[n]['reasons']) for n in combo)
    if flat_reasons.count('大冷回補') >= 2: bonus += 3.0
    if flat_reasons.count('絕對零度') >= 1: bonus += 1.5
    if flat_reasons.count('拖牌') >= 3: bonus += 2.5
    if any(combo[i+1] - combo[i] == 1 for i in range(4)):
        bonus += 2.0
    return bonus

def structure_bonus(combo):
    """
    結構平衡加分（優化五：奇偶1或4改為輕懲-0.5，全奇/全偶重懲-2.0）
    """
    bonus = 0.0
    odd = sum(1 for n in combo if n % 2 == 1)
    if odd in (2, 3):   bonus += 1.5   # 最佳比例，加分
    elif odd in (1, 4): bonus -= 0.5   # 輕懲（原+0.25改為-0.5）
    else:               bonus -= 2.0   # 全奇(5)或全偶(0)，重懲

    low  = sum(1 for n in combo if n <= 13)
    mid  = sum(1 for n in combo if 14 <= n <= 26)
    high = sum(1 for n in combo if n >= 27)
    empty_zones = [z for z in (low, mid, high) if z == 0]
    if len(empty_zones) == 0:
        bonus += 1.0
        balanced = sum(1 for z in (low, mid, high) if 1 <= z <= 2)
        if balanced == 3: bonus += 0.5
    elif len(empty_zones) == 1:
        bonus += 0.25
    else:
        bonus -= 1.5
    return bonus


def get_dual_pair_score(combo, pair_weights):
    pairs = list(combinations(combo, 2))
    best_val = 0
    for p1, p2 in combinations(pairs, 2):
        if not set(p1).intersection(set(p2)):
            val = pair_weights.get(p1, 0) + pair_weights.get(p2, 0)
            if val > best_val:
                best_val = val
    return best_val

def get_markov_bonus(combo, history):
    bonus = 0.0
    if len(history) < 3: return 0.0
    
    prev_draw = history[-1]['nums']
    prev2_draw = history[-2]['nums']
    
    for n in combo:
        for p in prev_draw:
            diff = abs(n - p)
            if diff <= 1:
                bonus += 2.5  
                break
            elif diff == 2:
                bonus += 0.8  
                break

    for n in combo:
        for p in prev_draw:
            if n == p + 1:
                if (p - 1) in prev2_draw:
                    bonus += 3.0 
                    break
            elif n == p - 1:
                if (p + 1) in prev2_draw:
                    bonus += 3.0 
                    break
                
    flipped_prev = []
    for p in prev_draw:
        flip_str = str(p).zfill(2)[::-1]
        flip_int = int(flip_str)
        if 1 <= flip_int <= 39 and flip_int != p:
            flipped_prev.append(flip_int)
            
    for n in combo:
        if n in flipped_prev:
            bonus += 3.0 
            
    recent_diffs = set()
    lookback_depth = min(7, len(history) - 1)
    
    for i in range(1, lookback_depth + 1):
        curr_draw = history[-i]['nums']
        older_draw = history[-i - 1]['nums']
        for p1 in older_draw:
            for p2 in curr_draw:
                recent_diffs.add(p2 - p1)
            
    for p in prev_draw:
        for n in combo:
            if (n - p) in recent_diffs:
                bonus += 2.0
                break
                
    return bonus

def generate_combos_v83(final_pool, pair_stats_long, triplet_stats_long, history):
    row_map = {x['num']: x for x in final_pool}
    recent20_sets = [tuple(sorted(r['nums'])) for r in history[-20:]]
    
    sum_history_map = {}
    for row in history:
        s = sum(row['nums'])
        if s not in sum_history_map: sum_history_map[s] = []
        sum_history_map[s].append(set(row['nums']))

    recent_10_draws = history[-10:] if len(history) >= 10 else history[:]
    target_ma_sum = sum(sum(r['nums']) for r in recent_10_draws) / max(1, len(recent_10_draws))
    
    T1 = [x['num'] for x in final_pool[0:6]]   
    T2 = [x['num'] for x in final_pool[6:12]]  
    T3 = [x['num'] for x in final_pool[12:18]] 
    T4 = [x['num'] for x in final_pool[18:24]] 
    T5 = [x['num'] for x in final_pool[24:30]] 

    pool_nums = [x['num'] for x in final_pool]
    pair_weights = {}
    for a, b in combinations(pool_nums, 2):
        pair_key = tuple(sorted((a, b)))
        pair_weights[pair_key] = pair_stats_long.get(pair_key, 0)

    dynamic_pair_weights = {k: v for k, v in pair_weights.items()}
    global_num_usage = Counter()
    final_combos = []

    # 引擎 1：🔥 狙擊矛 (2組)
    spear_templates = [
        ((2, 1, 1, 1, 0), "🔥 狙擊矛 (熱區前鋒陣)"),
        ((1, 2, 1, 1, 0), "🔥 狙擊矛 (溫號中堅陣)")
    ]

    for t_idx in range(2):
        t1, t2, t3, t4, t5 = spear_templates[t_idx][0]
        strat_name = spear_templates[t_idx][1]
        best_combo, best_score, b_dp, b_tri, b_sum, b_shared = None, -9999, 0, 0, 0, 0
        
        for parts in itertools.product(combinations(T1, t1), combinations(T2, t2), combinations(T3, t3), combinations(T4, t4), combinations(T5, t5)):
            c = tuple(sorted(parts[0] + parts[1] + parts[2] + parts[3] + parts[4]))
            if c in recent20_sets: continue
            if any(global_num_usage[n] >= 2 for n in c): continue
            
            c_sum = sum(c)
            dp_sc = get_dual_pair_score(c, dynamic_pair_weights)
            tri_sc = sum(triplet_stats_long.get(tuple(sorted(tri)), 0) for tri in combinations(c, 3))
            max_shared = max([len(set(c) & past) for past in sum_history_map.get(c_sum, [])] + [0])
            sum_bonus = 25.0 if max_shared >= 3 else (5.0 if max_shared == 2 else 0)
            res = combo_bucket_bonus_v82(c, row_map)
            sum_dev = abs(c_sum - target_ma_sum)
            ma_penalty = max(0, sum_dev - 25) * 0.15  # 優化四：偏離25以內免懲
            
            markov_bonus = get_markov_bonus(c, history)
            
            overlap_pen = 0
            for sel, _, _, _, _, _ in final_combos:
                inter = len(set(c) & set(sel))
                if inter >= 3: overlap_pen += 2000
                elif inter == 2: overlap_pen += 50
                
            score = (dp_sc * 2.5) + (tri_sc * 3.5) + sum_bonus + (res * 3.0) + markov_bonus + structure_bonus(c) - ma_penalty - overlap_pen
            
            if score > best_score:
                best_score = score
                best_combo = c
                b_dp, b_tri, b_sum, b_shared = dp_sc, tri_sc, c_sum, max_shared
                
        if best_combo:
            final_combos.append((best_combo, round(b_dp, 2), round(b_tri, 2), b_sum, b_shared, strat_name))
            for n in best_combo: global_num_usage[n] += 1
            for a, b in combinations(best_combo, 2):
                pair_key = tuple(sorted((a, b)))
                dynamic_pair_weights[pair_key] = dynamic_pair_weights.get(pair_key, 0) * 0.1

    # 引擎 2：🛡️ 鐵壁盾 (2組)
    T1_shield = [n for n in T1 if global_num_usage[n] == 0]
    T2_shield = [n for n in T2 if global_num_usage[n] == 0]
    T3_shield = [n for n in T3 if global_num_usage[n] == 0]
    T4_shield = [n for n in T4 if global_num_usage[n] == 0]
    T5_shield = [n for n in T5 if global_num_usage[n] == 0]

    shield_templates = [
        ((0, 1, 1, 1, 2), "🛡️ 鐵壁盾 (暗星逆襲陣)"),
        ((1, 0, 1, 2, 1), "🛡️ 鐵壁盾 (冷溫伏擊陣)")
    ]

    for t_idx in range(2):
        t1, t2, t3, t4, t5 = shield_templates[t_idx][0]
        strat_name = shield_templates[t_idx][1]
        
        while len(T1_shield) < t1: T1_shield.append(random.choice(T1))
        while len(T2_shield) < t2: T2_shield.append(random.choice(T2))
        while len(T3_shield) < t3: T3_shield.append(random.choice(T3))
        while len(T4_shield) < t4: T4_shield.append(random.choice(T4))
        while len(T5_shield) < t5: T5_shield.append(random.choice(T5))
        
        best_combo, best_score, b_dp, b_tri, b_sum, b_shared = None, -9999, 0, 0, 0, 0
        
        for parts in itertools.product(combinations(set(T1_shield), t1), combinations(set(T2_shield), t2), combinations(set(T3_shield), t3), combinations(set(T4_shield), t4), combinations(set(T5_shield), t5)):
            c = tuple(sorted(parts[0] + parts[1] + parts[2] + parts[3] + parts[4]))
            if len(set(c)) < 5: continue
            if c in recent20_sets: continue
            if any(global_num_usage[n] >= 2 for n in c): continue
            
            c_sum = sum(c)
            dp_sc = get_dual_pair_score(c, dynamic_pair_weights)
            tri_sc = sum(triplet_stats_long.get(tuple(sorted(tri)), 0) for tri in combinations(c, 3))
            max_shared = max([len(set(c) & past) for past in sum_history_map.get(c_sum, [])] + [0])
            sum_bonus = 25.0 if max_shared >= 3 else (5.0 if max_shared == 2 else 0)
            res = combo_bucket_bonus_v82(c, row_map)
            sum_dev = abs(c_sum - target_ma_sum)
            ma_penalty = max(0, sum_dev - 25) * 0.15  # 優化四：偏離25以內免懲
            markov_bonus = get_markov_bonus(c, history)
            
            overlap_pen = 0
            for sel, _, _, _, _, _ in final_combos:
                inter = len(set(c) & set(sel))
                if inter >= 3: overlap_pen += 2000
                elif inter == 2: overlap_pen += 50
                
            score = (dp_sc * 2.5) + (tri_sc * 3.5) + sum_bonus + (res * 3.0) + markov_bonus + structure_bonus(c) - ma_penalty - overlap_pen
            
            if score > best_score:
                best_score = score
                best_combo = c
                b_dp, b_tri, b_sum, b_shared = dp_sc, tri_sc, c_sum, max_shared
                
        if best_combo:
            final_combos.append((best_combo, round(b_dp, 2), round(b_tri, 2), b_sum, b_shared, strat_name))
            for n in best_combo: global_num_usage[n] += 1
            for a, b in combinations(best_combo, 2):
                pair_key = tuple(sorted((a, b)))
                dynamic_pair_weights[pair_key] = dynamic_pair_weights.get(pair_key, 0) * 0.1

    # 引擎 3：🌪️ 混沌核心 (2組)
    used_so_far = set()
    for cand in final_combos: used_so_far.update(cand[0])
        
    unused_nums = [n for n in pool_nums if n not in used_so_far]
    b_pool = list(unused_nums)
    if len(b_pool) < 10:
        pad_cands = [n for n in pool_nums if n not in b_pool]
        b_pool.extend(pad_cands[:10 - len(b_pool)])
        
    # 固定退火隨機種子：必須在 shuffle 之前設定
    # 確保初始狀態和整個退火過程完全一致
    random.seed(539)
    random.shuffle(b_pool)
    current_state_C = [b_pool[0:5], b_pool[5:10]]
    
    def calc_C_score(state):
        total_score = 0
        for c in state:
            c_sum = sum(c)
            c_set = set(c)
            syn = sum(pair_weights.get(tuple(sorted((a, b))), 0) for a, b in combinations(c, 2))
            tri = sum(triplet_stats_long.get(tuple(sorted((a, b, c_))), 0) for a, b, c_ in combinations(c, 3))
            max_shared = max([len(c_set & past) for past in sum_history_map.get(c_sum, [])] + [0])
            sum_b = 25.0 if max_shared >= 3 else 0
            markov_bonus = get_markov_bonus(c, history)
            
            pen = 0
            if any(global_num_usage[n] >= 2 for n in c): pen += 5000
            for sel, _, _, _, _, _ in final_combos:
                if len(set(c) & set(sel)) >= 3: pen += 2000
                
            total_score += (syn * 1.5) + (tri * 5.0) + sum_b + (markov_bonus * 1.5) + structure_bonus(c) - pen
        return total_score

    best_state_C = copy.deepcopy(current_state_C)
    best_score_C = calc_C_score(current_state_C)
    current_score_C = best_score_C

    T = 100.0
    cooling_rate = 0.95
    min_T = 0.1

    while T > min_T:
        for _ in range(60):
            new_state = copy.deepcopy(current_state_C)
            t1_idx, t2_idx = 0, 1
            n1_idx, n2_idx = random.randint(0, 4), random.randint(0, 4)
            n1, n2 = new_state[t1_idx][n1_idx], new_state[t2_idx][n2_idx]
            if n2 in new_state[t1_idx] or n1 in new_state[t2_idx]: continue
            new_state[t1_idx][n1_idx], new_state[t2_idx][n2_idx] = n2, n1
            new_state[t1_idx].sort()
            new_state[t2_idx].sort()

            new_score = calc_C_score(new_state)
            if new_score > current_score_C or math.exp((new_score - current_score_C) / T) > random.random():
                current_score_C = new_score
                current_state_C = new_state
                if current_score_C > best_score_C:
                    best_score_C = current_score_C
                    best_state_C = copy.deepcopy(current_state_C)
        T *= cooling_rate

    # 退火結束，還原隨機狀態，避免影響其他隨機邏輯
    random.seed(None)
        
    for c_list in best_state_C:
        c = tuple(sorted(c_list))
        dp_score = get_dual_pair_score(c, pair_weights)
        tri_score = sum(triplet_stats_long.get(tuple(sorted((a, b, c_))), 0) for a, b, c_ in combinations(c, 3))
        c_sum = sum(c)
        max_shared = max([len(set(c) & past) for past in sum_history_map.get(c_sum, [])] + [0])
        final_combos.append((c, round(dp_score, 2), round(tri_score, 2), c_sum, max_shared, "🌪️ 混沌核心 (退火突變陣)"))

    # =========================================================================
    # 引擎 4：⚡ 深矛延伸 (2組，偏重T2/T3中高分號碼區)
    # =========================================================================
    deep_templates = [
        ((0, 2, 2, 1, 0), "⚡ 深矛延伸 (中堅突破陣)"),
        ((1, 1, 2, 0, 1), "⚡ 深矛延伸 (冷中融合陣)")
    ]

    for t_idx in range(2):
        t1, t2, t3, t4, t5 = deep_templates[t_idx][0]
        strat_name = deep_templates[t_idx][1]
        best_combo, best_score, b_dp, b_tri, b_sum, b_shared = None, -9999, 0, 0, 0, 0

        src_T1 = T1 if t1 > 0 else []
        src_T2 = T2 if t2 > 0 else []
        src_T3 = T3 if t3 > 0 else []
        src_T4 = T4 if t4 > 0 else []
        src_T5 = T5 if t5 > 0 else []

        iter_parts = []
        for tn, src in zip([t1,t2,t3,t4,t5],[src_T1,src_T2,src_T3,src_T4,src_T5]):
            if tn == 0:
                iter_parts.append([tuple()])
            else:
                cands = list(combinations(src, tn)) if len(src) >= tn else []
                if not cands:
                    iter_parts.append([tuple()])
                else:
                    iter_parts.append(cands)

        for parts in itertools.product(*iter_parts):
            c = tuple(sorted(parts[0] + parts[1] + parts[2] + parts[3] + parts[4]))
            if len(set(c)) < 5: continue
            if c in recent20_sets: continue
            if any(global_num_usage[n] >= 2 for n in c): continue

            c_sum = sum(c)
            dp_sc = get_dual_pair_score(c, dynamic_pair_weights)
            tri_sc = sum(triplet_stats_long.get(tuple(sorted(tri)), 0) for tri in combinations(c, 3))
            max_shared = max([len(set(c) & past) for past in sum_history_map.get(c_sum, [])] + [0])
            sum_bonus = 25.0 if max_shared >= 3 else (5.0 if max_shared == 2 else 0)
            res = combo_bucket_bonus_v82(c, row_map)
            sum_dev = abs(c_sum - target_ma_sum)
            ma_penalty = max(0, sum_dev - 25) * 0.15  # 優化四：偏離25以內免懲
            markov_bonus = get_markov_bonus(c, history)

            overlap_pen = 0
            for sel, _, _, _, _, _ in final_combos:
                inter = len(set(c) & set(sel))
                if inter >= 3: overlap_pen += 2000
                elif inter == 2: overlap_pen += 50

            score = (dp_sc * 2.5) + (tri_sc * 3.5) + sum_bonus + (res * 3.0) + markov_bonus + structure_bonus(c) - ma_penalty - overlap_pen

            if score > best_score:
                best_score = score
                best_combo = c
                b_dp, b_tri, b_sum, b_shared = dp_sc, tri_sc, c_sum, max_shared

        if best_combo:
            final_combos.append((best_combo, round(b_dp, 2), round(b_tri, 2), b_sum, b_shared, strat_name))
            for n in best_combo: global_num_usage[n] += 1
            for a, b in combinations(best_combo, 2):
                pair_key = tuple(sorted((a, b)))
                dynamic_pair_weights[pair_key] = dynamic_pair_weights.get(pair_key, 0) * 0.1

    # =========================================================================
    # 引擎 5：🧊 冷號突破 (2組，偏重T4/T5冷門號碼突破)
    # =========================================================================
    cold_templates = [
        ((1, 0, 1, 2, 1), "🧊 冷號突破 (暗冰爆發陣)"),
        ((0, 1, 0, 2, 2), "🧊 冷號突破 (極寒逆擊陣)")
    ]

    # 冷號突破的候選池：允許使用次數 <= 1 的號碼，不足時從原始池補足
    T4_ext = [n for n in T4 if global_num_usage[n] <= 1]
    T5_ext = [n for n in T5 if global_num_usage[n] <= 1]
    if len(T4_ext) < 2: T4_ext = list(T4)
    if len(T5_ext) < 2: T5_ext = list(T5)

    for t_idx in range(2):
        t1, t2, t3, t4, t5 = cold_templates[t_idx][0]
        strat_name = cold_templates[t_idx][1]
        best_combo, best_score, b_dp, b_tri, b_sum, b_shared = None, -9999, 0, 0, 0, 0

        src_list = [T1, T2, T3, T4_ext, T5_ext]
        tns = [t1, t2, t3, t4, t5]

        iter_parts = []
        for tn, src in zip(tns, src_list):
            if tn == 0:
                iter_parts.append([tuple()])
            else:
                cands = list(combinations(src, tn)) if len(src) >= tn else []
                if not cands:
                    iter_parts.append([tuple()])
                else:
                    iter_parts.append(cands)

        for parts in itertools.product(*iter_parts):
            c = tuple(sorted(parts[0] + parts[1] + parts[2] + parts[3] + parts[4]))
            if len(set(c)) < 5: continue
            if c in recent20_sets: continue
            # 冷號突破放寬使用次數限制為 >= 3 才跳過
            if any(global_num_usage[n] >= 3 for n in c): continue

            c_sum = sum(c)
            dp_sc = get_dual_pair_score(c, dynamic_pair_weights)
            tri_sc = sum(triplet_stats_long.get(tuple(sorted(tri)), 0) for tri in combinations(c, 3))
            max_shared = max([len(set(c) & past) for past in sum_history_map.get(c_sum, [])] + [0])
            sum_bonus = 25.0 if max_shared >= 3 else (5.0 if max_shared == 2 else 0)
            res = combo_bucket_bonus_v82(c, row_map)
            sum_dev = abs(c_sum - target_ma_sum)
            ma_penalty = max(0, sum_dev - 25) * 0.15  # 優化四：偏離25以內免懲
            markov_bonus = get_markov_bonus(c, history)

            # 冷號突破放寬重疊懲罰
            overlap_pen = 0
            for sel, _, _, _, _, _ in final_combos:
                inter = len(set(c) & set(sel))
                if inter >= 4: overlap_pen += 2000
                elif inter == 3: overlap_pen += 200
                elif inter == 2: overlap_pen += 30

            score = (dp_sc * 2.5) + (tri_sc * 3.5) + sum_bonus + (res * 3.0) + markov_bonus + structure_bonus(c) - ma_penalty - overlap_pen

            if score > best_score:
                best_score = score
                best_combo = c
                b_dp, b_tri, b_sum, b_shared = dp_sc, tri_sc, c_sum, max_shared

        if best_combo:
            final_combos.append((best_combo, round(b_dp, 2), round(b_tri, 2), b_sum, b_shared, strat_name))
            for n in best_combo: global_num_usage[n] += 1
            for a, b in combinations(best_combo, 2):
                pair_key = tuple(sorted((a, b)))
                dynamic_pair_weights[pair_key] = dynamic_pair_weights.get(pair_key, 0) * 0.1

    # =========================================================================
    # 引擎 6：🌀 第二退火 (2組，種子1539，探索不同解空間)
    # =========================================================================
    # 第二退火候選池：從全部pool_nums中取使用次數最少的10顆
    usage_sorted = sorted(pool_nums, key=lambda n: global_num_usage[n])
    b_pool_2 = list(usage_sorted[:10])
    if len(b_pool_2) < 10:
        pad = [n for n in pool_nums if n not in b_pool_2]
        b_pool_2.extend(pad[:10 - len(b_pool_2)])

    random.seed(1539)  # 不同種子，探索不同解空間
    random.shuffle(b_pool_2)
    current_state_C2 = [b_pool_2[0:5], b_pool_2[5:10]]

    def calc_C_score2(state):
        total_score = 0
        for c in state:
            c_sum = sum(c)
            c_set = set(c)
            syn = sum(pair_weights.get(tuple(sorted((a, b))), 0) for a, b in combinations(c, 2))
            tri = sum(triplet_stats_long.get(tuple(sorted((a, b, c_))), 0) for a, b, c_ in combinations(c, 3))
            max_shared = max([len(c_set & past) for past in sum_history_map.get(c_sum, [])] + [0])
            sum_b = 25.0 if max_shared >= 3 else 0
            markov_bonus = get_markov_bonus(c, history)

            # 第二退火放寬懲罰（允許更多探索）
            pen = 0
            if any(global_num_usage[n] >= 3 for n in c): pen += 5000
            for sel, _, _, _, _, _ in final_combos:
                inter = len(set(c) & set(sel))
                if inter >= 4: pen += 2000
                elif inter == 3: pen += 300

            total_score += (syn * 1.5) + (tri * 5.0) + sum_b + (markov_bonus * 1.5) + structure_bonus(c) - pen
        return total_score

    best_state_C2 = copy.deepcopy(current_state_C2)
    best_score_C2 = calc_C_score2(current_state_C2)
    current_score_C2 = best_score_C2

    T2_anneal = 100.0
    cooling_rate2 = 0.95
    min_T2 = 0.1

    while T2_anneal > min_T2:
        for _ in range(60):
            new_state2 = copy.deepcopy(current_state_C2)
            t1_idx2, t2_idx2 = 0, 1
            n1_idx2 = random.randint(0, 4)
            n2_idx2 = random.randint(0, 4)
            n1_2 = new_state2[t1_idx2][n1_idx2]
            n2_2 = new_state2[t2_idx2][n2_idx2]
            if n2_2 in new_state2[t1_idx2] or n1_2 in new_state2[t2_idx2]: continue
            new_state2[t1_idx2][n1_idx2] = n2_2
            new_state2[t2_idx2][n2_idx2] = n1_2
            new_state2[t1_idx2].sort()
            new_state2[t2_idx2].sort()

            new_score2 = calc_C_score2(new_state2)
            if new_score2 > current_score_C2 or math.exp((new_score2 - current_score_C2) / T2_anneal) > random.random():
                current_score_C2 = new_score2
                current_state_C2 = new_state2
                if current_score_C2 > best_score_C2:
                    best_score_C2 = current_score_C2
                    best_state_C2 = copy.deepcopy(current_state_C2)
        T2_anneal *= cooling_rate2

    # 第二退火結束，還原隨機狀態
    random.seed(None)

    for c_list in best_state_C2:
        c = tuple(sorted(c_list))
        dp_score = get_dual_pair_score(c, pair_weights)
        tri_score = sum(triplet_stats_long.get(tuple(sorted((a, b, c_))), 0) for a, b, c_ in combinations(c, 3))
        c_sum = sum(c)
        max_shared = max([len(set(c) & past) for past in sum_history_map.get(c_sum, [])] + [0])
        final_combos.append((c, round(dp_score, 2), round(tri_score, 2), c_sum, max_shared, "🌀 第二退火 (異空突破陣)"))

    # =========================================================================
    # 約束三：全號段覆蓋補洞（確保1~39每顆號碼至少出現一次）
    # V111改善：只針對第5~12組（index 4~11）做替換
    #           前4組（狙擊矛+鐵壁盾）完全保護，維持高品質追求3顆
    #           後8組（退火+延伸+冷號突破）負責全覆蓋責任
    # =========================================================================
    transition_full = build_transition_matrix(history)
    full_score_map = {}
    for n in range(1, 40):
        sc, reasons, meta = score_number_v82(n, history, transition_full)
        full_score_map[n] = sc

    all_39 = set(range(1, 40))
    used_nums = set(n for c, *_ in final_combos for n in c)
    missing_nums = sorted(all_39 - used_nums)

    if missing_nums:
        num_counts = Counter(n for c, *_ in final_combos for n in c)

        for m in missing_nums:
            best_swap = None
            best_metric = -999999

            # 只掃描 index 4~11（第5~12組），保護前4組不被補洞
            for i, (c_tup, dp_sc, tri_sc, c_sum, c_shared, strat) in enumerate(final_combos):
                if i < 4:
                    continue   # ✅ 前4組（狙擊矛+鐵壁盾）完全保護

                for n in list(c_tup):
                    if num_counts[n] <= 1:
                        continue   # 唯一出現，不能替換

                    new_c = tuple(sorted(
                        [x for x in c_tup if x != n] + [m]
                    ))

                    # 計算替換前後的綜合分數差
                    new_dp  = get_dual_pair_score(new_c, pair_weights)
                    new_tri = sum(
                        triplet_stats_long.get(tuple(sorted(t)), 0)
                        for t in combinations(new_c, 3)
                    )
                    new_markov = get_markov_bonus(new_c, history)

                    # 評分變化
                    old_s = (dp_sc * 2.5) + (tri_sc * 3.5) + structure_bonus(c_tup)
                    new_s = (new_dp * 2.5) + (new_tri * 3.5) + structure_bonus(new_c) + (new_markov * 0.3)
                    delta = new_s - old_s

                    # 被換掉的號碼評分越高越不該換
                    anchor_pen    = full_score_map.get(n, 0) * 3.0
                    # 補入號碼評分越高越好
                    addition_bon  = full_score_map.get(m, 0) * 1.5
                    # 結構改善額外獎勵
                    struct_reward = (structure_bonus(new_c) - structure_bonus(c_tup)) * 2.0

                    metric = delta - anchor_pen + addition_bon + struct_reward

                    if metric > best_metric:
                        best_metric = metric
                        best_swap = (i, n, new_c, new_dp, new_tri)

            if best_swap:
                idx, removed, new_c, new_dp, new_tri = best_swap
                _, dp_sc, tri_sc, c_sum, c_shared, strat = final_combos[idx]
                tag = strat if "(全覆蓋補洞)" in strat else strat + " (全覆蓋補洞)"
                final_combos[idx] = (
                    new_c,
                    round(new_dp, 2),
                    round(new_tri, 2),
                    sum(new_c),
                    c_shared,
                    tag
                )
                num_counts[removed] -= 1
                num_counts[m]       += 1

    return final_combos, round(target_ma_sum, 1)


# =========================================================================
# 修改功能：選項 3 (區間詳細回測) 改為 CSV 輸出，與選項一的算法完全同步
# =========================================================================
def run_detailed_backtest(data, ref_start_idx, test_start_idx, test_end_idx):
    results = []
    total_steps = test_end_idx - test_start_idx + 1
    if total_steps <= 0:
        print("起始回測期數必須小於或等於結束回測期數！")
        return

    print(f'\n[系統提示] 啟動區間詳細回測 (共 {total_steps} 期)...')
    for step, target_idx in enumerate(range(test_start_idx, test_end_idx + 1), 1):
        sys.stdout.write(f'\r回測進度: [{step}/{total_steps}] 正在計算第 {data[target_idx]["draw"]} 期...')
        sys.stdout.flush()
        
        # 【關鍵修復】：使用指定的歷史參考起點，確保算法和選項一完全相同
        history = data[ref_start_idx:target_idx]
        if len(history) < 15: 
            continue
        
        all_scored, pair_stats_long, triplet_stats_long = build_pool_v82(history)
        combos, _ = generate_combos_v83(all_scored, pair_stats_long, triplet_stats_long, history)
        
        actual = data[target_idx]['nums']
        hits_per_combo = [len(set(combo[0]) & set(actual)) for combo in combos]
        best_hit = max(hits_per_combo, default=0)
        
        results.append({
            'draw': data[target_idx]['draw'],
            'actual': actual,
            'hits_per_combo': hits_per_combo,
            'best_hit': best_hit
        })
    print()
    
    if not results:
        print("無有效回測結果 (可能是歷史資料不足)。")
        return
        
    total = len(results)
    best_hits = [r['best_hit'] for r in results]
    avg_hit = sum(best_hits) / total
    ge2 = sum(1 for x in best_hits if x >= 2)
    ge3 = sum(1 for x in best_hits if x >= 3)
    ge4 = sum(1 for x in best_hits if x >= 4)
    
    # 準備寫入 CSV
    start_draw = results[0]["draw"]
    end_draw = results[-1]["draw"]
    csv_filename = f"詳細回測報告_{start_draw}_{end_draw}.csv"

    try:
        with open(csv_filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            # 寫入摘要資訊
            writer.writerow(['📊 V115 輕量優化版 詳細回測報告'])
            writer.writerow([f'回測區間', f'第 {start_draw} 期 ~ 第 {end_draw} 期', f'共 {total} 期'])
            writer.writerow(['⭐ 平均最佳命中', f'{avg_hit:.2f} 顆'])
            writer.writerow(['🎯 最佳命中 ≥2顆', f'{ge2} 次 ({ge2 * 100 / total:.2f}%)'])
            writer.writerow(['🔥 最佳命中 ≥3顆', f'{ge3} 次 ({ge3 * 100 / total:.2f}%)'])
            writer.writerow(['👑 最佳命中 4顆', f'{ge4} 次 ({ge4 * 100 / total:.2f}%)'])
            writer.writerow([]) # 空行分隔

            # 寫入明細標頭
            num_combos = len(results[0]['hits_per_combo'])
            headers = ['期別', '實際開獎', '最高命中'] + [f'第{i+1}組命中' for i in range(num_combos)]
            writer.writerow(headers)

            # 寫入每期明細
            for r in results:
                actual_str = str(r['actual'])
                row = [r['draw'], actual_str, f"{r['best_hit']}顆"]
                for hit in r['hits_per_combo']:
                    row.append(f"{hit}顆")
                writer.writerow(row)

        print(f"✅ 區間詳細回測已完成！")
        print(f"📂 分析報告與明細已成功儲存至檔案：{csv_filename}")
        
    except Exception as e:
        print(f"⚠️ 寫入 CSV 時發生錯誤：{e}")

def backtest(data, start_idx, end_idx):
    results = []
    start_bt = max(start_idx + 10, end_idx - BACKTEST_LOOKBACK + 1)
    total_steps = end_idx + 1 - start_bt
    if total_steps <= 0: return []
    print(f'\n[系統提示] 啟動 V115 輕量優化版，正在進行 {total_steps} 期極速回測...')
    for step, target_idx in enumerate(range(start_bt, end_idx + 1), 1):
        sys.stdout.write(f'\r回測進度: [{step}/{total_steps}] 正在計算第 {data[target_idx]["draw"]} 期...')
        sys.stdout.flush()
        history = data[start_idx:target_idx]
        if len(history) < 15: continue
        all_scored, pair_stats_long, triplet_stats_long = build_pool_v82(history)
        combos, _ = generate_combos_v83(all_scored, pair_stats_long, triplet_stats_long, history)
        actual = data[target_idx]['nums']
        best_hit = max((len(set(combo[0]) & set(actual)) for combo in combos), default=0)
        results.append(best_hit)
    print()
    return results

def draw_map(data):
    return {row['draw']: idx for idx, row in enumerate(data)}

def print_header(data, encoding):
    print('=' * 90)
    print('539 V115 輕量優化版 (奇偶強化+和值放寬+全覆蓋 gichier基底)')
    print('=' * 90)
    print(f'資料來源檔：{CSV_NAME}')
    print(f'讀取編碼：{encoding}')
    print(f'資料總筆數：{len(data)}')
    print(f'資料區間：第{data[0]["draw"]}期 ~ 第{data[-1]["draw"]}期')
    print()

def ask_mode():
    print('請選擇模式：')
    print('1. 驗證已開獎期數（可看命中與回測）')
    print('2. 預測未來未開期數（僅輸出候選組合）')
    print('3. 自訂區間詳細回測（回測明細儲存為 CSV）')
    mode = input('輸入 1, 2 或 3：').strip()
    if mode not in {'1', '2', '3'}: raise Exception('錯誤')
    return mode

def ask_draw(prompt):
    return int(input(prompt).strip())

def print_colored_history(history, highlight_nums):
    if not highlight_nums: return
    color_map = {num: COLORS[i % len(COLORS)] for i, num in enumerate(highlight_nums[:6])}
    print('\n' + '=' * 90)
    print('歷史開獎紀錄（顏色標示）：')
    for num, color in color_map.items():
        print(f'{color} {num:02d} {RESET_COLOR}', end='  ')
    print('\n' + '-' * 90)
    for row in history:
        nums_str = [f"{color_map[n]} {n:02d} {RESET_COLOR}" if n in color_map else f" {n:02d} " for n in row['nums']]
        print(f"第 {row['draw']} 期 [{row['date']}] : " + "  ".join(nums_str))
    print('=' * 90 + '\n')

def main():
    os.system('') 
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    data, encoding = load_csv(CSV_NAME)
    dmap = draw_map(data)
    print_header(data, encoding)

    mode = ask_mode()

    # 執行模式 3 (CSV匯出) 並結束
    if mode == '3':
        print('\n請輸入要使用的【參考歷史資料】區間 (決定分析的起點)')
        ref_start_draw = ask_draw('起始參考期數：')
        ref_end_draw = ask_draw('結束參考期數 (通常為最新一期)：')
        
        print('\n請輸入要【產生報表的回測】區間 (您想測試的範圍)')
        test_start_draw = ask_draw('起始回測期數：')
        test_end_draw = ask_draw('結束回測期數：')
        
        if ref_start_draw not in dmap or ref_end_draw not in dmap or test_start_draw not in dmap or test_end_draw not in dmap:
            raise Exception('期數不存在')
        
        ref_start_idx = dmap[ref_start_draw]
        test_start_idx = dmap[test_start_draw]
        test_end_idx = dmap[test_end_draw]
        
        run_detailed_backtest(data, ref_start_idx, test_start_idx, test_end_idx)
        print('\n請按任意鍵繼續 . . .')
        input()
        return

    print('\n請輸入要使用的歷史資料區間 (建議選擇近期連續期數)')
    hist_start_draw = ask_draw('起始期數：')
    hist_end_draw = ask_draw('結束期數：')

    if hist_start_draw not in dmap or hist_end_draw not in dmap:
        raise Exception('期數不存在')
    start_idx, end_idx = dmap[hist_start_draw], dmap[hist_end_draw]

    track_input = input('\n追蹤號碼 (空白分隔，免追蹤按 Enter)：').strip()
    highlight_nums = [int(x) for x in track_input.split() if x.isdigit()][:6] if track_input else []

    if mode == '1':
        target_draw = hist_end_draw + 1
        if target_draw not in dmap:
            raise Exception('驗證模式下，目標期數必須已存在於資料庫')
        target_row = data[dmap[target_draw]]
    else:
        print('\n未來預測模式：')
        target_draw = ask_draw('要預測的未開獎期數：')
        target_row = None

    history = data[start_idx:end_idx + 1]
    print_colored_history(history, highlight_nums)

    all_scored, pair_stats_long, triplet_stats_long = build_pool_v82(history)
    combos, target_ma_sum = generate_combos_v83(all_scored, pair_stats_long, triplet_stats_long, history)

    print('\n' + '=' * 90)
    print(f'預測目標：第{target_draw}期')
    print(f'🎯 總和引力標靶：過去 10 期動態平均總和 = {target_ma_sum}')
    print('=' * 90)
    
    print('\n深水核心池 (24 顆六維強勢號 + 6 顆極端冷號)：')
    print([x['num'] for x in all_scored[:30]])

    print('\n預測組合（V115 輕量優化版：奇偶強化+和值放寬+全覆蓋）：')

    # 覆蓋率統計
    covered_set = set(n for c, *_ in combos for n in c)
    uncovered   = sorted(set(range(1, 40)) - covered_set)
    print(f'📊 本次 12 組彩券共涵蓋 {len(covered_set)} 個不重複號碼！')
    if not uncovered:
        print('✅ 達成 1~39 號碼 100% 絕對全覆蓋！')
    else:
        print(f'⚠️ 未覆蓋號碼：{uncovered}')
    print('-' * 90)

    for i, (combo, dp_val, tri_val, c_sum, max_shared, strat_name) in enumerate(combos):
        odd  = sum(1 for n in combo if n % 2 == 1)
        low  = sum(1 for n in combo if n <= 13)
        mid  = sum(1 for n in combo if 14 <= n <= 26)
        high = sum(1 for n in combo if n >= 27)
        sb   = structure_bonus(combo)
        print(f'第 {i+1:2d} 組【{strat_name}】: {list(combo)} | '
              f'雙核二星={dp_val} | 3星={tri_val} | 總和={c_sum}(同和={max_shared}) | '
              f'奇{odd}偶{5-odd} 低{low}中{mid}高{high} 結構+{sb:.1f}')

    if mode == '1' and target_row:
        actual = target_row['nums']
        print('\n實際開獎：', actual)
        print(f'實際總和：{sum(actual)}')
        print('\n命中：')
        for i, (combo, _, _, _, _, _) in enumerate(combos, 1):
            print(f'第{i}組：{len(set(combo) & set(actual))}顆')

        bt = backtest(data, start_idx, end_idx)
        if bt:
            print('\nV115 回測摘要：')
            print(f'樣本數：{len(bt)}')
            print(f'平均最佳命中：{round(sum(bt) / len(bt), 2)} 顆')
            print(f'最佳命中≥2顆：{sum(1 for x in bt if x >= 2)} 次 ({round(sum(1 for x in bt if x >= 2) * 100 / len(bt), 2)}%)')
            print(f'最佳命中≥3顆：{sum(1 for x in bt if x >= 3)} 次 ({round(sum(1 for x in bt if x >= 3) * 100 / len(bt), 2)}%)')
            print(f'最佳命中 4 顆：{sum(1 for x in bt if x == 4)} 次 ({round(sum(1 for x in bt if x == 4) * 100 / len(bt), 2)}%)')

    print('\n請按任意鍵繼續 . . .')
    input()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'\n錯誤：{e}')
        input()
# =================================================================
# 👇 以下為 API 雲端接孔 (Cloud API Entry Point) 👇
# =================================================================
def get_prediction(zodiac_id: int):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, CSV_NAME)

        # 呼叫無敵防呆版 load_csv
        data, _ = load_csv(csv_path)
        if not data:
            return {"status": "error", "message": "今彩539 CSV 讀取失敗或格式錯誤"}

        history = data[:]
        all_scored, pair_stats, triplet_stats = build_pool_v82(history)
        combos, _ = generate_combos_v83(all_scored, pair_stats, triplet_stats, history)

        # 根據生肖挑選一組號碼
        chosen_idx = (zodiac_id - 1) % len(combos)
        
        # 🛑 終極防呆：正確解開大禮包，只取第一個元素（純號碼陣列）
        raw_combo = combos[chosen_idx]
        if isinstance(raw_combo, tuple) and isinstance(raw_combo[0], (list, tuple)):
            chosen_combo = list(raw_combo[0])
        else:
            chosen_combo = list(raw_combo)
            
        # 洗淨資料：確保陣列裡面通通都是數字，並且只拿 5 顆球
        chosen_combo = [int(x) for x in chosen_combo if str(x).isdigit()][:5]
        
        # 抓取下一期期號
        try:
            next_issue_str = str(int(history[-1]['draw']) + 1)
        except:
            next_issue_str = "最新一期"

        return {
            "status": "success",
            "type": "jincai539",
            "issue_number": next_issue_str,
            "zone1": chosen_combo,
            "zone2": None 
        }
    except Exception as e:
        return {"status": "error", "message": f"今彩539引擎發生錯誤: {str(e)}"}