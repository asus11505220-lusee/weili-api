# -*- coding: utf-8 -*-
import csv
import os
import random
import numpy as np
from numpy.fft import fft, fftfreq
from collections import Counter
from itertools import combinations, permutations
from datetime import datetime

# ================= 配置區 =================
WEILI_CSV = '威力彩_歷史資料.csv'
C539_CSV = '今彩539_歷史資料.csv'
ENCODINGS = ['utf-8-sig', 'cp950', 'big5', 'utf-8']

COLORS = [
    '\033[93m', '\033[92m', '\033[96m', '\033[95m', '\033[94m'
]
RESET = '\033[0m'

# ================= 載入與工具區 =================
def parse_date(date_str):
    date_str = str(date_str).replace('/', '-').strip()
    try:
        if len(date_str.split('-')[0]) == 3: 
            parts = date_str.split('-')
            date_str = f"{int(parts[0])+1911}-{parts[1]}-{parts[2]}"
        return datetime.strptime(date_str, '%Y-%m-%d')
    except:
        return datetime.min

# 🔴 核心修改：彈性讀取 CSV 資料，相容 539 與威力彩，略過無效或缺漏的欄位
def load_csv(filename):
    if not os.path.exists(filename): return []
    last_err = None
    for enc in ENCODINGS:
        try:
            with open(filename, 'r', encoding=enc, newline='') as f:
                rows = list(csv.DictReader(f))
            normalized = []
            for r in rows:
                try:
                    period = str(r.get('期別', r.get('period', ''))).strip()
                    date_str = str(r.get('開獎日期', r.get('date', ''))).strip()
                    nums = []
                    
                    # 彈性讀取 1~6 個號碼（抓不到或為空值就忽略，不會觸發 KeyError 或 ValueError）
                    for key in ['獎號1', '獎號2', '獎號3', '獎號4', '獎號5', '獎號6', 'n1', 'n2', 'n3', 'n4', 'n5', 'n6']:
                        val = r.get(key, '').strip()
                        if val.isdigit():
                            nums.append(int(val))
                            
                    # 彈性讀取第二區（539 沒這個欄位就維持 None）
                    zone2 = None
                    for z2_key in ['第二區', '特別號', 'zone2']:
                        z2_val = r.get(z2_key, '').strip()
                        if z2_val.isdigit():
                            zone2 = int(z2_val)
                            break
                            
                    # 只要有抓到數字（無論是5個還是6個），就視為有效資料
                    if period and len(nums) >= 5:
                        data_row = {'draw': period, 'date_str': date_str, 'date_obj': parse_date(date_str), 'nums': sorted(nums)}
                        if zone2 is not None: 
                            data_row['zone2'] = zone2
                        normalized.append(data_row)
                except Exception:
                    # 如果單行解析發生無法預期的錯誤，直接略過該行，不讓引擎崩潰
                    continue
                    
            if normalized: return normalized
        except Exception as e:
            last_err = e
    return []

# ================= Layer 4: 跨彩種 539 化學鍵結 =================
def get_539_chemical_bonds(history_539, target_date):
    if not history_539: return [], Counter()
    valid_539 = [r for r in history_539 if r['date_obj'] <= target_date]
    recent_539_10 = valid_539[-10:] if len(valid_539) >= 10 else valid_539
    recent_539_30 = valid_539[-30:] if len(valid_539) >= 30 else valid_539
    
    single_counter = Counter()
    for row in recent_539_30:
        for n in row['nums']: single_counter[n] += 1
    top_10_singles = [x[0] for x in single_counter.most_common(10)]
    
    bond_counter = Counter()
    for row in recent_539_10:
        valid_nums = [n for n in row['nums'] if n <= 38]
        for a, b in combinations(valid_nums, 2):
            bond_counter[tuple(sorted((a, b)))] += 1
            
    strong_bonds = {k: v for k, v in bond_counter.items() if v >= 1}
    return top_10_singles, strong_bonds

# ================= Layer 2 & 3: 多維時間窗規律分析 =================
def build_advanced_stats(history_wl, bonds_539):
    pair_count = Counter()
    triplet_count = Counter()
    z1_z2_pair_count = Counter() 
    total_draws = len(history_wl)
    
    p5_counter, p10_counter, p15_counter, p20_counter = Counter(), Counter(), Counter(), Counter()
    single_freq = {5: Counter(), 10: Counter(), 15: Counter(), 20: Counter()}

    for idx, row in enumerate(history_wl):
        draws_ago = total_draws - idx
        nums = row['nums']
        z2 = row.get('zone2')
        
        w = 15.0 if draws_ago <= 5 else (8.0 if draws_ago <= 10 else (6.0 if draws_ago <= 15 else (4.0 if draws_ago <= 20 else 1.0)))
        
        for n in nums:
            if draws_ago <= 5: single_freq[5][n] += 1
            if draws_ago <= 10: single_freq[10][n] += 1
            if draws_ago <= 15: single_freq[15][n] += 1
            if draws_ago <= 20: single_freq[20][n] += 1

        for a, b in combinations(nums, 2):
            pair = tuple(sorted((a, b)))
            pair_count[pair] += w
            if draws_ago <= 5: p5_counter[pair] += 1
            if draws_ago <= 10: p10_counter[pair] += 1
            if draws_ago <= 15: p15_counter[pair] += 1
            if draws_ago <= 20: p20_counter[pair] += 1

        for tri in combinations(nums, 3):
            triplet_count[tuple(sorted(tri))] += w * 1.5 
            
        if z2:
            for z1 in nums:
                z1_z2_pair_count[(z1, z2)] += w

    for (a, b), count in bonds_539.items():
        pair_count[(a, b)] += (count * 15.0)

    # V17 強化：近5期出現2次以上的pair = 「超強共價鍵」×5 額外加成
    for pair, cnt in p5_counter.items():
        if cnt >= 2:
            pair_count[pair] += cnt * 60.0   # 超強鍵能，讓退火強制聚合

    # V17 強化：近10期出現的triplet加重（三元共振節點）
    # 找 triplet 在 p10 中的共現次數
    trip10 = Counter()
    for row in (history_wl[-10:] if len(history_wl)>=10 else history_wl):
        for tri in combinations(row['nums'], 3):
            trip10[tuple(sorted(tri))] += 1
    for tri, cnt in trip10.items():
        if cnt >= 2:
            triplet_count[tri] += cnt * 80.0  # 近10期強三元組，大幅加成

    return pair_count, triplet_count, z1_z2_pair_count, p5_counter, p10_counter, p15_counter, p20_counter, single_freq

# ================= 🧪 第一區：V18 化學軌域引擎（歷史黑名單+近期衰減+三元核心固定）=================
def generate_zone1_hedging_matrix(single_freq, pair_stats, triplet_stats, p5, p10, p15, p20, bonds_539, mc_runs=36, history_wl=None):
    
    # 🎯【核心修正 1】：鎖定隨機亂數種子，保證相同資料產出相同結果
    if history_wl:
        random.seed(history_wl[-1]['draw'])
    else:
        random.seed(42) # Fallback

    # 建立歷史開獎黑名單
    forbidden_set = set()
    if history_wl:
        for row in history_wl:
            forbidden_set.add(tuple(sorted(row['nums'])))

    # ── Step1：先算 pair30/橋接節點（後面矩陣加成需要它）──
    pair30 = Counter()
    strong_pairs = []
    node_connections = Counter()
    potential_trips = {}
    top_trips = []

    if history_wl:
        for row in (history_wl[-30:] if len(history_wl)>=30 else history_wl):
            for a, b in combinations(row['nums'], 2):
                pair30[tuple(sorted((a,b)))] += 1

    strong_pairs = [p for p, c in pair30.items() if c >= 2]
    for p in strong_pairs:
        node_connections[p[0]] += 1
        node_connections[p[1]] += 1

    # 🎯【核心修正 2】：消除字典/集合排序隨機性，同分時比較數字大小
    sorted_nodes = sorted(node_connections.items(), key=lambda x: (-x[1], x[0]))

    # ── Step2：pair矩陣：近30期衰減(50%) + 全歷史V13加權(50%) + 橋接加成 ──
    recent_pair_mat = [[0.0]*40 for _ in range(40)]
    if history_wl:
        # 近30期衰減（50%）
        for age, row in enumerate(reversed(history_wl[-30:])):
            w = max(0, 30 - age) / 30.0
            for a, b in combinations(row['nums'], 2):
                recent_pair_mat[a][b] += w * 5.0
                recent_pair_mat[b][a] += w * 5.0
        # 全歷史V13加權（50%）
        total_h = len(history_wl)
        for idx, row in enumerate(history_wl):
            ago = total_h - idx
            w = 15.0 if ago<=5 else (8.0 if ago<=10 else (6.0 if ago<=15 else (4.0 if ago<=20 else 1.0)))
            for a, b in combinations(row['nums'], 2):
                recent_pair_mat[a][b] += w * 0.5
                recent_pair_mat[b][a] += w * 0.5
        # 橋接節點加成
        if strong_pairs and node_connections:
            top_bridge_nodes = [n for n, _ in sorted_nodes[:5]]
            for p in strong_pairs:
                a, b = p
                if a in top_bridge_nodes or b in top_bridge_nodes:
                    recent_pair_mat[a][b] += pair30[p] * 3.0
                    recent_pair_mat[b][a] += pair30[p] * 3.0

    # 從橋接節點構建潛在三元組
    potential_trips = {}
    for n, _ in sorted_nodes[:10]:
        connected_nums = set()
        for p in strong_pairs:
            if n in p:
                other = p[0] if p[1] == n else p[1]
                connected_nums.add(other)
        for a, b in combinations(sorted(connected_nums), 2):
            trip = tuple(sorted([n, a, b]))
            score = (pair30.get(tuple(sorted((n, a))), 0) +
                     pair30.get(tuple(sorted((n, b))), 0) +
                     pair30.get(tuple(sorted((a, b))), 0))
            if score > potential_trips.get(trip, 0):
                potential_trips[trip] = score

    # 取pair總分最高的前4個三元組作為骨架候選 (強制防綁定排序隨機性)
    top_trips = [t for t, _ in sorted(potential_trips.items(), key=lambda x: (-x[1], x[0]))[:4]]

    # 若 pair延伸法找不到足夠的，退回近20期triplet計數法
    if len(top_trips) < 4:
        trip20 = Counter()
        if history_wl:
            for row in (history_wl[-20:] if len(history_wl)>=20 else history_wl):
                for tri in combinations(row['nums'], 3):
                    trip20[tuple(sorted(tri))] += 1
        sorted_trip20 = sorted(trip20.items(), key=lambda x: (-x[1], x[0]))
        top_trips += [t for t, _ in sorted_trip20[:4] if t not in top_trips]
        top_trips = top_trips[:4]

    # ── 熱度計算 ──
    hotness = {n: (single_freq[5][n]*4 + single_freq[10][n]*3 +
                   single_freq[15][n]*2 + single_freq[20][n]*1)
               for n in range(1, 39)}
    # 🎯【核心修正 3】：熱度平手時，以號碼大小決定先後順序
    ranked = sorted(hotness.keys(), key=lambda k: (hotness[k], k), reverse=True)

    HOT  = set(ranked[:10])
    WARM = set(ranked[10:25])
    COLD = set(ranked[25:])

    role_array = [0]*40
    for n in HOT:  role_array[n] = 1
    for n in WARM: role_array[n] = 2
    for n in COLD: role_array[n] = 3

    shell_of = [n % 5 for n in range(40)]

    s539_single = Counter()
    for (a, b), cnt in bonds_539.items():
        s539_single[a] += cnt; s539_single[b] += cnt
    wl_recent10 = single_freq[10]
    empty_orbital_charge = {n: s539_single.get(n,0)*2.5 - wl_recent10.get(n,0)*2.0
                            for n in range(1,39)}

    # ── 矩陣預算（只用近30期衰減pair，不用全歷史）──
    pair_mat = recent_pair_mat
    trip_mat = [[[0.0]*40 for _ in range(40)] for _ in range(40)]
    for k, v in triplet_stats.items():
        if len(k) == 3:
            for p in permutations(k):
                trip_mat[p[0]][p[1]][p[2]] = v

    def calc_group_chem(g):
        score = 0.0
        n = len(g)
        for i in range(n):
            for j in range(i+1, n):
                score += pair_mat[g[i]][g[j]]
                for kk in range(j+1, n):
                    score += trip_mat[g[i]][g[j]][g[kk]]
        for ni in g:
            eoc = empty_orbital_charge.get(ni, 0)
            if eoc > 0: score += eoc * 8.0
        shell_count = Counter(shell_of[ni] for ni in g)
        for sh, cnt in shell_count.items():
            if cnt > 3: score -= (cnt-3)*150
            elif cnt == 3: score -= 30
        has_hot  = sum(1 for ni in g if role_array[ni]==1)
        has_cold = sum(1 for ni in g if role_array[ni]==3)
        if has_hot>=1 and has_cold>=1:
            score += has_hot * has_cold * 25.0
        sorted_g = sorted(g)
        gaps = [sorted_g[i+1]-sorted_g[i] for i in range(len(sorted_g)-1)]
        variety = sum([any(gp<=3 for gp in gaps), any(4<=gp<=7 for gp in gaps), any(gp>7 for gp in gaps)])
        score += (variety-1)*40.0
        # 歷史黑名單懲罰
        if tuple(sorted(g)) in forbidden_set:
            score -= 99999
        return score

    def calc_global_penalties(grps):
        pen = 0.0
        hot_role = warm_role = cold_role = 0
        shell_cov = []
        for g in grps:
            h = w = c = 0
            for ni in g:
                r = role_array[ni]
                if r==1: h+=1
                elif r==2: w+=1
                elif r==3: c+=1
            if h>=3: hot_role+=1
            if w>=3: warm_role+=1
            if c>=2 and h>=1: cold_role+=1
            shell_cov.append(len(set(shell_of[ni] for ni in g)))

        # ── V25 修正：依實際組數動態縮放閾值（原設計是8組）──
        # 原8組設計：50%熱組/25%溫組/25%冷組/62.5%覆蓋4層
        # 12組縮放：6/3/3/7  → 完整保留 V20 的比例邏輯
        n_g    = len(grps)
        ratio  = n_g / 8.0
        t_hot  = max(2, int(4 * ratio))   # 8組→4, 12組→6
        t_warm = max(1, int(2 * ratio))   # 8組→2, 12組→3
        t_cold = max(1, int(2 * ratio))   # 8組→2, 12組→3
        t_sh   = max(3, int(5 * ratio))   # 8組→5, 12組→7

        if hot_role  < t_hot : pen -= (t_hot  - hot_role ) * 500
        if warm_role < t_warm: pen -= (t_warm - warm_role) * 500
        if cold_role < t_cold: pen -= (t_cold - cold_role) * 500
        groups_4plus = sum(1 for s in shell_cov if s>=4)
        if groups_4plus < t_sh: pen -= (t_sh - groups_4plus) * 200
        return pen

    pool = list(range(1, 39))
    # 12組×6個 = 72個token
    # pool = range(1,39) = 38個基底
    # 還需要 72-38 = 34個補充
    # 修正：避免 ranked[:15] 和 ranked[:10] 重複導致Top10出現3次
    # 改為：Top12各加1份(12個) + Top12~25溫號各加1份(13個) + 最冷9個各1份(9個) = 34個
    fillers = ranked[:12] + ranked[12:25] + ranked[-9:]
    pool.extend(fillers)
    # pool大小 = 38 + 12 + 13 + 9 = 72，剛好分12組×6個

    supreme_best_groups = None
    supreme_best_score  = -999999

    import math

    for _ in range(mc_runs):
        best_groups = None
        best_score  = -999999

        for attempt in range(15):
            sets = [set() for _ in range(12)]

            # ── 三元核心固定：第1~4組先植入強triplet ──
            for gi, core_tri in enumerate(top_trips[:4]):
                for n in core_tri:
                    sets[gi].add(n)

            tokens = pool.copy()
            random.shuffle(tokens)
            success = True
            for t in tokens:
                available = [i for i in range(12) if len(sets[i])<6 and t not in sets[i]]
                if not available:
                    # 退化：放棄三元核心，全部重置
                    sets = [set() for _ in range(12)]
                    random.shuffle(tokens)
                    for t2 in tokens:
                        av2 = [i for i in range(12) if len(sets[i])<6 and t2 not in sets[i]]
                        if av2: sets[random.choice(av2)].add(t2)
                    success = all(len(s)==6 for s in sets)
                    break
                sets[random.choice(available)].add(t)

            if not all(len(s)==6 for s in sets): continue

            # 🎯【核心修正 4】：消除 Set 取值順序造成的雜湊隨機性
            groups = [sorted(list(s)) for s in sets]
            grp_scores  = [calc_group_chem(g) for g in groups]
            current_syn = sum(grp_scores)
            current_pen = calc_global_penalties(groups)
            current_total = current_syn + current_pen

            T = 120.0; T_min = 0.5
            alpha = (T_min / T) ** (1.0 / 3000)

            for step in range(3000):
                T *= alpha
                g1_idx, g2_idx = random.sample(range(12), 2)
                e1_idx = random.randint(0, len(groups[g1_idx])-1)
                e2_idx = random.randint(0, len(groups[g2_idx])-1)
                e1 = groups[g1_idx][e1_idx]
                e2 = groups[g2_idx][e2_idx]

                if (e2 not in groups[g1_idx] or e2==e1) and \
                   (e1 not in groups[g2_idx] or e1==e2):
                    groups[g1_idx][e1_idx] = e2
                    groups[g2_idx][e2_idx] = e1
                    new_g1 = calc_group_chem(groups[g1_idx])
                    new_g2 = calc_group_chem(groups[g2_idx])
                    new_syn   = current_syn - grp_scores[g1_idx] - grp_scores[g2_idx] + new_g1 + new_g2
                    new_pen   = calc_global_penalties(groups)
                    new_total = new_syn + new_pen
                    delta = new_total - current_total
                    if delta >= 0 or random.random() < math.exp(max(delta/T, -500)):
                        current_total = new_total
                        current_syn   = new_syn
                        current_pen   = new_pen
                        grp_scores[g1_idx] = new_g1
                        grp_scores[g2_idx] = new_g2
                    else:
                        groups[g1_idx][e1_idx] = e1
                        groups[g2_idx][e2_idx] = e2

            if current_total > best_score:
                best_score  = current_total
                best_groups = [g.copy() for g in groups]

        if best_groups and best_score > supreme_best_score:
            supreme_best_score  = best_score
            supreme_best_groups = best_groups

    if not supreme_best_groups:
        raise Exception("化學退火失敗，請重新執行程式。")

    # 🎯【核心修正 5】：解決平分時因為記憶體位置不同的隨機亂流
    supreme_best_groups.sort(key=lambda g: (sum(hotness[n] for n in g), tuple(g)), reverse=True)

    final_sets = []
    for i, g in enumerate(supreme_best_groups):
        lst = sorted(list(g))
        bond = calc_group_chem(lst)
        shells = len(set(shell_of[n] for n in lst))
        hot_cnt  = sum(1 for n in lst if n in HOT)
        cold_cnt = sum(1 for n in lst if n in COLD)
        is_forbidden = '⛔重複' if tuple(lst) in forbidden_set else ''
        if hot_cnt>=3:    charge_tag="⚡陽離子"
        elif cold_cnt>=3: charge_tag="🔵陰離子"
        else:             charge_tag="⚖️ 中性分子"
        if   i<4: ctype=f"🔥 {charge_tag}({hot_cnt}熱{cold_cnt}冷/{shells}層){is_forbidden}"
        elif i<6: ctype=f"🌊 {charge_tag}({hot_cnt}熱{cold_cnt}冷/{shells}層){is_forbidden}"
        else:     ctype=f"🧊 {charge_tag}({hot_cnt}熱{cold_cnt}冷/{shells}層){is_forbidden}"
        final_sets.append({"combo":lst, "c_sum":sum(lst), "internal_syn":bond, "type":ctype})

    return final_sets

# ================= 第二區：聲波干涉引擎 V11 =================
def wave_zone2_predict(history_wl, top_n=5):
    if len(history_wl) < 12:
        return 4, {i: 1/8 for i in range(1,9)}, []

    z2_seq = np.array([r['zone2'] for r in history_wl if 'zone2' in r], dtype=float)
    N = len(z2_seq)
    mean_val = z2_seq.mean()
    centered = z2_seq - mean_val

    # ── 1. FFT 頻譜，找主頻 ──
    Z = fft(centered)
    freqs = fftfreq(N)
    power = np.abs(Z) ** 2
    pos_idx = np.where(freqs > 0)[0]
    top_idx = pos_idx[np.argsort(power[pos_idx])[::-1][:top_n]]

    # ── 2. 相位干涉分析（近段 vs 中段）──
    seg = max(N // 3, 8)
    s_mid  = centered[seg: 2*seg]
    s_late = centered[2*seg:]
    Zm = fft(s_mid);  Zl = fft(s_late)
    
    constructive_boost = 0.0   
    destructive_damp   = 0.0   

    wave_log = ['─── 聲波干涉分析 ───']
    for k in range(1, min(6, seg//2)):
        if k >= len(Zm) or k >= len(Zl):
            break
        period = seg / k
        phase_m = np.angle(Zm[k])
        phase_l = np.angle(Zl[k])
        dp = (phase_l - phase_m + np.pi) % (2*np.pi) - np.pi
        if abs(dp) < np.pi / 3:
            constructive_boost += power[top_idx[0]] ** 0.1
            tag = '📈 建設性加強'
        elif abs(dp) > 2 * np.pi / 3:
            destructive_damp += 1.0
            tag = '📉 破壞性消除'
        else:
            tag = '↔️  側向震盪'
        wave_log.append(f'  週期≈{period:.1f}期  相位差={np.degrees(dp):+.0f}°  {tag}')

    # ── 3. 主頻波形延伸，預測 t=N（下一期）──
    pred_wave = mean_val
    for idx in top_idx:
        amp   = Z[idx] / N
        freq  = freqs[idx]
        pred_wave += (amp * np.exp(2j * np.pi * freq * N)).real * 2

    # 干涉修正
    net_interference = constructive_boost - destructive_damp * 0.5
    pred_adjusted = pred_wave + net_interference * 0.3
    pred_clamped = float(np.clip(pred_adjusted, 1, 8))

    # ── 4. 高斯共振分佈 + 冷門保底 ──
    sigma = 1.4
    raw_resonance = {}
    for target in range(1, 9):
        gauss = np.exp(-0.5 * ((target - pred_clamped) / sigma) ** 2)
        recent_hits = list(z2_seq[-20:]).count(target)
        raw_resonance[target] = gauss * (1 + recent_hits * 0.15)

    FLOOR = 0.04
    total_raw = sum(raw_resonance.values())
    for k in raw_resonance:
        if raw_resonance[k] / total_raw < FLOOR:
            raw_resonance[k] = total_raw * FLOOR   

    total = sum(raw_resonance.values())
    resonance = {k: v / total for k, v in raw_resonance.items()}
    pred_top = max(resonance, key=resonance.get)

    wave_log.append(f'  主頻預測原始值: {pred_wave:.3f}  →  干涉修正後: {pred_adjusted:.3f}')
    wave_log.append(f'  🎯 聲波最強共振號碼: 【 {pred_top:02d} 】  (共振強度: {resonance[pred_top]*100:.1f}%)')
    wave_log.append('  號碼共振分佈:')
    for k in sorted(resonance, key=resonance.get, reverse=True):
        bar = '█' * max(1, int(resonance[k] * 40))
        wave_log.append(f'    號碼 {k}: {bar}  {resonance[k]*100:.1f}%')

    return pred_top, resonance, wave_log

# ================= 第二區：V12 聲波排名綁組配對 =================
def assign_zone2_perfect_match(zone1_combos, z1_z2_pair_count, history_wl):
    recent30 = history_wl[-30:] if history_wl else []
    recent10 = history_wl[-10:] if history_wl else []
    recent5  = history_wl[-5:]  if history_wl else []

    z2_hot30 = Counter(r['zone2'] for r in recent30 if 'zone2' in r)
    z2_hot10 = Counter(r['zone2'] for r in recent10 if 'zone2' in r)
    z2_hot5  = Counter(r['zone2'] for r in recent5  if 'zone2' in r)
    sum_counts = Counter(sum(r['nums']) for r in history_wl) if history_wl else Counter()

    z2_options = list(range(1, 9))
    n_groups = len(zone1_combos)   

    # ── Step 1：聲波共振排名 ──
    _, resonance, _ = wave_zone2_predict(history_wl)
    # 🎯【核心修正 6】：平分時強制防亂流排序
    ranked_z2 = sorted(z2_options, key=lambda z: (resonance.get(z, 0), z), reverse=True)

    # ── Step 2：依共振強度決定各號碼分配組數
    # 修正：正確支援任意 n_groups，確保 slot_plan 長度 == n_groups
    slot_plan = []
    if n_groups <= 8:
        # ≤8組：按原始邏輯，末名可能分不到
        base_slots = [2, 1, 1, 1, 1, 1, 1, 0]
        for i in range(8 - n_groups):
            base_slots[7 - i] = 0
    else:
        # >8組（如12組）：每個號碼至少1組，多出的名額按共振強度由高到低補
        base_slots = [1] * 8          # 每個號碼先保1組
        extra = n_groups - 8          # 多出的名額（12-8=4）
        for i in range(extra):
            base_slots[i % 3] += 1   # 排名前3的號碼輪流多拿

    for z2, slots in zip(ranked_z2, base_slots):
        for _ in range(slots):
            slot_plan.append(z2)
    # 防呆：確保長度恰好等於 n_groups
    slot_plan = slot_plan[:n_groups]
    while len(slot_plan) < n_groups:
        slot_plan.append(ranked_z2[0])

    # ── Step 3：計算每組對每個第二區的聯合鍵結分 ──
    bond_scores = []
    for combo_dict in zone1_combos:
        combo = combo_dict['combo']
        row = {}
        for z2 in z2_options:
            bond = sum(z1_z2_pair_count.get((z1, z2), 0) for z1 in combo)
            hot  = z2_hot30.get(z2,0)*1.0 + z2_hot10.get(z2,0)*2.0 + z2_hot5.get(z2,0)*3.0
            row[z2] = bond + hot
        bond_scores.append(row)

    assigned_z2    = [None] * n_groups
    assigned_score = [0.0]  * n_groups
    group_used     = [False] * n_groups

    for target_z2 in slot_plan:
        best_g = -1
        best_b = -1.0
        for g in range(n_groups):
            if not group_used[g]:
                b = bond_scores[g][target_z2]
                if b > best_b:
                    best_b = b
                    best_g = g
        if best_g >= 0:
            assigned_z2[best_g]    = target_z2
            assigned_score[best_g] = best_b
            group_used[best_g]     = True

    for g in range(n_groups):
        if assigned_z2[g] is None:
            assigned_z2[g]    = ranked_z2[0]
            assigned_score[g] = bond_scores[g][ranked_z2[0]]

    for i, combo_dict in enumerate(zone1_combos):
        combo_dict['sum_occ'] = sum_counts.get(combo_dict['c_sum'], 0)

    return assigned_z2, assigned_score

# ================= 互動選單與主程式 =================
def ask_mode():
    print('\n請選擇模式：')
    print('1. 驗證單一期數 (輸入歷史期數，盲測並比對實際開獎)')
    print('2. 預測未來期數 (使用所有資料，產出下一期最新推薦號碼)')
    print('3. 批量回測驗證 (測試過去 N 期，統計綜合命中率)')
    while True:
        m = input('👉 輸入 1, 2 或 3：').strip()
        if m in ['1', '2', '3']: return m

def main():
    try: os.chdir(os.path.dirname(os.path.abspath(__file__)))
    except: pass
        
    os.system('') 
    print('=' * 95)
    print('🚀 威力彩降耗產生器 V25 (12組+懲罰動態縮放：保留V20核心，閾值比例修正)')
    print('=' * 95)
    
    history_wl = load_csv(WEILI_CSV)
    history_539 = load_csv(C539_CSV)
    
    if history_wl: 
        wl_start = history_wl[0]['draw']
        wl_end = history_wl[-1]['draw']
        print(f"✅ 成功載入 {len(history_wl)} 筆威力彩歷史資料 (期數區間: {wl_start} ~ {wl_end})")
    else: 
        return print(f"❌ 錯誤：未找到 {WEILI_CSV}！")
        
    if history_539: 
        c539_start = history_539[0]['draw']
        c539_end = history_539[-1]['draw']
        print(f"✅ 成功載入 {len(history_539)} 筆今彩539歷史資料 (期數區間: {c539_start} ~ {c539_end})")

    mode = ask_mode()
    
    if mode == '1':
        dmap = {row['draw']: idx for idx, row in enumerate(history_wl)}
        while True:
            target_draw = input('\n請輸入要驗證的「目標期別」(例如 115000039)：').strip()
            if target_draw in dmap:
                target_idx = dmap[target_draw]
                if target_idx == 0:
                    print("❌ 這是第一筆資料，無法回測。")
                    continue
                work_wl = history_wl[:target_idx]
                target_actual = history_wl[target_idx]
                break
            else:
                print("❌ 找不到該期數，請確認！")
                
        ref_date = work_wl[-1]['date_obj'] if work_wl else datetime.now()
        top_539_singles, bonds_539 = get_539_chemical_bonds(history_539, ref_date)
        pair_stats, triplet_stats, z1_z2_pair_count, p5, p10, p15, p20, single_freq = build_advanced_stats(work_wl, bonds_539)
        
        print('\n⚙️ 啟動 V33 霸王引擎 (單期驗證：啟動 100x 深度蒙地卡羅爆破)...')
        zone1_combos = generate_zone1_hedging_matrix(single_freq, pair_stats, triplet_stats, p5, p10, p15, p20, bonds_539, mc_runs=36, history_wl=work_wl)
        zone2_ordered, z2_scores = assign_zone2_perfect_match(zone1_combos, z1_z2_pair_count, work_wl)
        _, resonance, wave_log = wave_zone2_predict(work_wl)
        print('\n🌊 第二區聲波干涉分析報告')
        for line in wave_log: print(line)
        print('\n' + '=' * 95)
        print(f'🎯 威力彩 V25 (目標預測：第 {target_draw} 期)')
        print('   - 🔒 [固定種子] 最後期號為seed，相同資料永遠產出相同組合（V21新增）')
        print('   - ⚖️  [混合pair矩陣] 近30期50%+全歷史50%，底部風險分提升8倍（V20核心）')
        print('   - 🔗 [確定性排序] 平手節點/三元組以數字大小決定，消除隨機漂移（V21新增）')
        print('=' * 95)

        for i, combo_dict in enumerate(zone1_combos):
            z1 = combo_dict['combo']
            strategy = combo_dict['type']
            z2 = zone2_ordered[i]
            hit_z1 = len(set(z1) & set(target_actual['nums']))
            hit_z2 = "🌟中" if z2 == target_actual.get('zone2') else "沒中"
            wave_pct = resonance.get(z2, 0) * 100
            score_label = f"鍵結:{z2_scores[i]:.1f} 共振:{wave_pct:.0f}%"
            print(f"第 {i+1} 組 ({strategy}) : [ {'  '.join(f'{n:02d}' for n in z1)} ] ＋ 第二區：【 {z2:02d} 】({score_label}) | 命中: {hit_z1} 碼 / 區2: {hit_z2}")
        print('\n' + '-' * 95)
        actual_sum = sum(target_actual['nums'])
        print(f"💡 實際開獎結果：第一區 [ {'  '.join(f'{n:02d}' for n in target_actual['nums'])} ] ＋ 第二區：【 {target_actual.get('zone2', 0):02d} 】 (總和: {actual_sum})")

    elif mode == '2':
        work_wl = history_wl
        ref_date = work_wl[-1]['date_obj'] if work_wl else datetime.now()
        top_539_singles, bonds_539 = get_539_chemical_bonds(history_539, ref_date)
        pair_stats, triplet_stats, z1_z2_pair_count, p5, p10, p15, p20, single_freq = build_advanced_stats(work_wl, bonds_539)
        print('\n⚙️ 啟動 V22 引擎 (預測未來：100x 深度蒙地卡羅爆破)...')
        zone1_combos = generate_zone1_hedging_matrix(single_freq, pair_stats, triplet_stats, p5, p10, p15, p20, bonds_539, mc_runs=36, history_wl=work_wl)
        zone2_ordered, z2_scores = assign_zone2_perfect_match(zone1_combos, z1_z2_pair_count, work_wl)
        _, resonance, wave_log = wave_zone2_predict(work_wl)
        print('\n🌊 第二區聲波干涉分析報告')
        for line in wave_log: print(line)
        print('\n' + '=' * 95)
        print(f'🎯 威力彩 V25 (目標預測：未來的下一期)')
        print('   - 🔒 [固定種子] 最後期號為seed，相同資料永遠產出相同組合（V21新增）')
        print('   - ⚖️  [混合pair矩陣] 近30期50%+全歷史50%，底部風險分提升8倍（V20核心）')
        print('   - 🔗 [確定性排序] 平手節點/三元組以數字大小決定，消除隨機漂移（V21新增）')
        print('=' * 95)
        for i, combo_dict in enumerate(zone1_combos):
            z1 = combo_dict['combo']
            strategy = combo_dict['type']
            z2 = zone2_ordered[i]
            wave_pct = resonance.get(z2, 0) * 100
            score_label = f"鍵結:{z2_scores[i]:.1f} 共振:{wave_pct:.0f}%"
            print(f"第 {i+1} 組 ({strategy}) : [ {'  '.join(f'{n:02d}' for n in z1)} ] ＋ 第二區：【 {z2:02d} 】({score_label})")

    elif mode == '3':
        try:
            bt_count = int(input('\n請輸入要回測的最近期數 (例如 10, 30, 50)：').strip())
        except ValueError:
            return print("❌ 輸入錯誤，請輸入數字！")
            
        if bt_count > len(history_wl) - 1:
            bt_count = len(history_wl) - 1
            
        start_idx = len(history_wl) - bt_count
        print(f"\n🚀 啟動 V33 批量回測 (共 {bt_count} 期) ... 智能變速極速運算中，請耐心等候⏳")
        
        results_z1_max = [] 
        results_z2_hits = 0 
        total_z2_tickets = 0 
        
        for idx in range(start_idx, len(history_wl)):
            work_wl = history_wl[:idx]
            target_actual = history_wl[idx]
            ref_date = work_wl[-1]['date_obj']
            
            top_539_singles, bonds_539 = get_539_chemical_bonds(history_539, ref_date)
            pair_stats, triplet_stats, z1_z2_pair_count, p5, p10, p15, p20, single_freq = build_advanced_stats(work_wl, bonds_539)
            
            zone1_combos = generate_zone1_hedging_matrix(single_freq, pair_stats, triplet_stats, p5, p10, p15, p20, bonds_539, mc_runs=36, history_wl=work_wl)
            zone2_ordered, _ = assign_zone2_perfect_match(zone1_combos, z1_z2_pair_count, work_wl)
            
            period_max_z1 = 0
            period_hit_z2 = False
            
            for c_idx, c_info in enumerate(zone1_combos):
                z1 = c_info['combo']
                z2 = zone2_ordered[c_idx]
                
                hit_z1 = len(set(z1) & set(target_actual['nums']))
                if hit_z1 > period_max_z1:
                    period_max_z1 = hit_z1
                    
                if z2 == target_actual.get('zone2'):
                    period_hit_z2 = True
                    total_z2_tickets += 1
                    
            results_z1_max.append(period_max_z1)
            if period_hit_z2:
                results_z2_hits += 1
                
            print(f"✅ 第 {target_actual['draw']} 期驗證完成 -> 該期最高命中第一區: {period_max_z1} 顆, 第二區是否命中: {'是' if period_hit_z2 else '否'}")

        print("\n" + "="*80)
        print(f"📊 V33 智能變速對沖版 批量回測報告 (共 {bt_count} 期)")
        print("="*80)
        z1_counts = Counter(results_z1_max)
        print("🎯 第一區 [單期最高命中顆數] 統計：")
        for i in range(6, -1, -1):
            if i in z1_counts or i >= 4: 
                print(f"   - 最高命中 {i} 顆 : {z1_counts.get(i, 0):>3} 期")
                
        print("\n🎯 第二區 跨區配對命中統計：")
        print(f"   - 成功包牌命中第二區的期數 : {results_z2_hits} 期 (佔 {results_z2_hits/bt_count*100:.1f}%)")
        n_groups_actual = len(zone1_combos)
        print(f"   - 總計命中的第二區注數     : {total_z2_tickets} 注 (佔總產出 {bt_count*n_groups_actual} 注的 {total_z2_tickets/(bt_count*n_groups_actual)*100:.1f}%)")
        print("="*80)

    print('\n✅ 執行完畢！')

if __name__ == '__main__':
    main()

# =================================================================
# 👇 以下為 API 雲端接孔 (Cloud API Entry Point) 👇
# =================================================================
def get_prediction(zodiac_id: int):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(base_dir, WEILI_CSV)
        
        # 讀取威力彩歷史資料
        data = load_csv(csv_path) 
        if not data:
            return {"status": "error", "message": "威力彩 CSV 讀取失敗或無資料"}

        history_wl = data[:]
        
        # 威力彩 V25 化學軌域引擎需要讀取 539 資料作為鍵結參考
        c539_path = os.path.join(base_dir, C539_CSV)
        history_539 = load_csv(c539_path)
        
        ref_date = history_wl[-1]['date_obj'] if history_wl else datetime.now()

        # 精準對接原始程式碼的「多維時間窗」與「聲波干涉」連鎖函數
        top_539_singles, bonds_539 = get_539_chemical_bonds(history_539, ref_date)
        pair_stats, triplet_stats, z1_z2_pair_count, p5, p10, p15, p20, single_freq = build_advanced_stats(history_wl, bonds_539)
        zone1_combos = generate_zone1_hedging_matrix(single_freq, pair_stats, triplet_stats, p5, p10, p15, p20, bonds_539, mc_runs=36, history_wl=history_wl)
        zone2_ordered, z2_scores = assign_zone2_perfect_match(zone1_combos, z1_z2_pair_count, history_wl)

        # 根據生肖分配 12 組號碼
        chosen_idx = (zodiac_id - 1) % len(zone1_combos)
        chosen_zone1 = list(zone1_combos[chosen_idx]['combo'])
        chosen_zone2 = zone2_ordered[chosen_idx]
        
        # 安全轉型，避免字串相加錯誤導致 API 崩潰
        next_issue = str(int(data[-1]['draw']) + 1)
        
        return {
            "status": "success",
            "type": "weili",
            "issue_number": next_issue,
            "zone1": chosen_zone1,
            "zone2": chosen_zone2
        }
    except Exception as e:
        return {"status": "error", "message": f"威力彩引擎發生錯誤: {str(e)}"}