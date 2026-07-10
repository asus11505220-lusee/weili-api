import pandas as pd
import numpy as np
from collections import Counter
import random

class WaveEngine:
    def __init__(self, lookback=20):
        self.lookback = lookback
    def extract_wave(self, df, target_idx, number, dynamic_lookback=None):
        lb = dynamic_lookback if dynamic_lookback else self.lookback
        start_idx = max(0, target_idx - lb)
        window = df.iloc[start_idx:target_idx]
        wave = []
        for _, row in window.iterrows():
            nums = {row['n1'], row['n2'], row['n3'], row['n4'], row['n5'], row['n6']}
            wave.append(1 if number in nums else 0)
        while len(wave) < lb: wave.insert(0, 0)
        return np.array(wave)
    def calculate_v7_score(self, wave):
        score = 0.0
        if len(wave) < 5: return score
        recent_sum = sum(wave[-5:])
        if wave[-1] == 1: score += 0.4
        if recent_sum >= 2: score += 0.3
        if len(wave) >= 4 and wave[-1] == 0 and wave[-4] == 1: score += 0.5
        zero_streak = 0
        for i in reversed(wave):
            if i == 0: zero_streak += 1
            else: break
        if zero_streak >= 10: score += 0.8  
        if recent_sum >= 4: score -= 1.5  
        return score

class SpecialNumberEngine:
    def __init__(self, df_lotto):
        self.df_lotto = df_lotto
    def get_special_predictions(self, target_idx, lookback=30, top_k=5):
        # 混合「近15期(重近期)」與「近40期(中期熱度)」兩段窗口，讓排名較不黏著、
        # 且能回傳較長的候選清單供 12 組分散使用（涵蓋更多特別號）。
        # 註：特別號本質接近隨機，本清單僅提高涵蓋率，非保證命中。
        if 'special' not in self.df_lotto.columns: return []
        if target_idx <= 0: return []

        def win_scores(win, decay):
            s0 = max(0, target_idx - win)
            vals = self.df_lotto.iloc[s0:target_idx]['special'].dropna().astype(int).tolist()
            m = max(1, len(vals))
            sc = {}
            for i, v in enumerate(vals):
                if 1 <= v <= 49:
                    sc[v] = sc.get(v, 0.0) + 1.0 + decay * (i / m)
            return sc

        short = win_scores(15, 1.0)   # 近15期，權重偏近期
        mid   = win_scores(40, 0.5)   # 近40期，中期熱度
        scores = {n: short.get(n, 0.0) * 1.2 + mid.get(n, 0.0) * 0.6 for n in range(1, 50)}
        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        return [n for n, _ in ranked[:top_k]]

    def get_special_spread(self, target_idx, n_sets=12):
        """回傳 n_sets 個「彼此不同」的特別號候選，供各組分散押注（提高涵蓋率）。
           前段用熱門排名，不足則以尚未用到的號碼補齊，確保 12 組不重複。"""
        ranked = self.get_special_predictions(target_idx, top_k=49)
        if not ranked:
            return list(range(1, n_sets + 1))
        spread = ranked[:n_sets]
        if len(spread) < n_sets:
            for n in range(1, 50):
                if n not in spread:
                    spread.append(n)
                if len(spread) >= n_sets:
                    break
        return spread[:n_sets]

class CrossLotteryEngine:
    def __init__(self, daily539_df):
        self.df_539 = daily539_df
    def get_mapping_scores(self, target_date):
        scores = {i: 0.0 for i in range(1, 50)}
        if self.df_539 is not None and not self.df_539.empty and not pd.isna(target_date):
            mask = (self.df_539['date'] < target_date) & (self.df_539['date'] >= (target_date - pd.Timedelta(days=7)))
            recent_539 = self.df_539[mask]
            nums_539 = []
            for _, row in recent_539.iterrows():
                for k in ['n1', 'n2', 'n3', 'n4', 'n5']:
                    try: nums_539.append(int(float(row[k])))
                    except: pass
            for n in range(1, 50):
                if n <= 39:
                    c = nums_539.count(n)
                    if c == 1: scores[n] += 0.5
                    elif c >= 2: scores[n] += 1.2
                t = n % 10
                t_count = sum(1 for x in nums_539 if x % 10 == t)
                if t_count >= 3: scores[n] += (t_count * 0.4)
                else: scores[n] += (t_count * 0.2)
        return scores

class MicroAdjustmentEngine:
    def __init__(self, df_lotto):
        self.df_lotto = df_lotto
    def get_micro_scores(self, target_idx):
        scores = {i: 0.0 for i in range(1, 50)}
        if target_idx < 2: return scores
        prev_row = self.df_lotto.iloc[target_idx - 1]
        prev_prev_row = self.df_lotto.iloc[target_idx - 2]
        
        prev_draw = [int(float(prev_row[k])) for k in ['n1', 'n2', 'n3', 'n4', 'n5', 'n6'] if pd.notna(prev_row.get(k))]
        prev_prev_draw = [int(float(prev_prev_row[k])) for k in ['n1', 'n2', 'n3', 'n4', 'n5', 'n6'] if pd.notna(prev_prev_row.get(k))]
        if not prev_draw or not prev_prev_draw: return scores

        flipped_prev = {int(str(p).zfill(2)[::-1]) for p in prev_draw if 1 <= int(str(p).zfill(2)[::-1]) <= 49 and int(str(p).zfill(2)[::-1]) != p}
        recent_diffs = {p2 - p1 for p1 in prev_prev_draw for p2 in prev_draw}
                
        for n in range(1, 50):
            if any(abs(n - p) <= 1 for p in prev_draw): scores[n] += 1.5
            if n in flipped_prev: scores[n] += 3.0
            if any((n - p) in recent_diffs for p in prev_draw): scores[n] += 2.0
        return scores

class V7StructureEngine:
    """ Layer 21.2: V9.96 穩定定膽優化版 (定膽與連號脫鉤分離) """
    def __init__(self, base_engine, df_lotto, df_539=None):
        self.base_engine = base_engine  
        self.df_lotto = df_lotto
        self.df_539 = df_539
        self.wave_engine = WaveEngine()
        self.cross_engine = CrossLotteryEngine(df_539)
        self.special_engine = SpecialNumberEngine(df_lotto)
        self.micro_engine = MicroAdjustmentEngine(df_lotto)

    def _get_synergy_data(self, target_idx, target_date):
        lotto_pairs = Counter(); lotto_triplets = Counter() 
        start_idx = max(0, target_idx - 50)
        
        for _, row in self.df_lotto.iloc[start_idx:target_idx].iterrows():
            nums = sorted([int(float(row[k])) for k in ['n1', 'n2', 'n3', 'n4', 'n5', 'n6'] if pd.notna(row.get(k))])
            for i in range(len(nums)):
                for j in range(i+1, len(nums)):
                    lotto_pairs[(nums[i], nums[j])] += 1
                    for k_idx in range(j+1, len(nums)):
                        lotto_triplets[(nums[i], nums[j], nums[k_idx])] += 1
                    
        c539_pairs = Counter(); c539_triplets = Counter() 
        if self.df_539 is not None and not self.df_539.empty and not pd.isna(target_date):
            mask = (self.df_539['date'] < target_date) & (self.df_539['date'] >= (target_date - pd.Timedelta(days=60)))
            for _, row in self.df_539[mask].iterrows():
                nums = sorted([int(float(row[k])) for k in ['n1', 'n2', 'n3', 'n4', 'n5'] if pd.notna(row.get(k))])
                for i in range(len(nums)):
                    for j in range(i+1, len(nums)):
                        c539_pairs[(nums[i], nums[j])] += 1
                        for k_idx in range(j+1, len(nums)):
                            c539_triplets[(nums[i], nums[j], nums[k_idx])] += 1
                        
        return lotto_pairs, lotto_triplets, c539_pairs, c539_triplets

    def generate(self, target_idx, sets=10, custom_start_idx=None):
        random.seed(target_idx)
        pool_raw, detail, core_raw, _ = self.base_engine.generate(target_idx, sets=sets)
        
        # ✅ 穩定修正：539 cutoff = 前2期開獎日（不論何時執行、DB有幾筆，結果一致）
        if target_idx >= 2:
            target_date = pd.to_datetime(self.df_lotto.iloc[target_idx - 2]['date']).normalize()
        elif target_idx >= 1:
            target_date = pd.to_datetime(self.df_lotto.iloc[target_idx - 1]['date']).normalize()
        else:
            target_date = pd.Timestamp.today().normalize()
        
        # 維持趨勢回歸修正機制
        target_ma_sum = 150.0
        if target_idx >= 10:
            recent_10 = self.df_lotto.iloc[target_idx-10:target_idx]
            sums = []
            for _, row in recent_10.iterrows():
                s = sum([int(float(row[k])) for k in ['n1','n2','n3','n4','n5','n6'] if pd.notna(row.get(k))])
                sums.append(s)
            if len(sums) >= 5:
                recent_5_mean = np.mean(sums[-5:])
                trend = sums[-1] - sums[-3]                  
                target_ma_sum = recent_5_mean - trend * 0.3   
                target_ma_sum = max(80.0, min(220.0, target_ma_sum))  
            elif sums:
                target_ma_sum = np.mean(sums)

        c_scores = self.cross_engine.get_mapping_scores(target_date)
        m_scores = self.micro_engine.get_micro_scores(target_idx)
        v6_scores = {d['num']: d['score'] for d in detail}
        v6_reasons = {d['num']: d['reasons'] for d in detail} 
        history_lb = (target_idx - custom_start_idx) if custom_start_idx is not None else 20
        
        full_detail = []
        score_map = {}
        for n in range(1, 49 + 1):
            base_s = v6_scores.get(n, 0.0) 
            w_score = self.wave_engine.calculate_v7_score(self.wave_engine.extract_wave(self.df_lotto, target_idx, n, dynamic_lookback=history_lb))
            c_score = c_scores.get(n, 0.0)
            m_score = m_scores.get(n, 0.0)
            
            total_score = base_s + w_score + c_score + m_score
            score_map[n] = total_score
            
            reasons = v6_reasons.get(n, "") if isinstance(v6_reasons, dict) else ""
            if w_score != 0: reasons += f" | 波({w_score:+.1f})"
            if c_score >= 1.2: reasons += f" | 🔥539({c_score:+.1f})"
            if m_score >= 1.5: reasons += f" | ⚡動能({m_score:+.1f})"
            full_detail.append({'num': n, 'score': total_score, 'reasons': reasons})

        # ══ 近期高頻加成（集中火力）══
        # 分析近8期實際開獎號碼的頻率，高頻號碼加分
        # 使用 df_lotto.iloc[target_idx-8:target_idx]，同一 target_idx 永遠相同 → 穩定
        if target_idx >= 8:
            freq_window = 8
            freq_counter = {}
            for fi in range(max(0, target_idx - freq_window), target_idx):
                row = self.df_lotto.iloc[fi]
                for col in ['n1','n2','n3','n4','n5','n6']:
                    n = int(float(row[col]))
                    freq_counter[n] = freq_counter.get(n, 0) + 1
            # 最高頻的號碼最多加 +4.0，讓它在 score_map 中更突出
            max_freq = max(freq_counter.values()) if freq_counter else 1
            for n, cnt in freq_counter.items():
                freq_bonus = (cnt / max_freq) * 4.0
                score_map[n] = score_map.get(n, 0) + freq_bonus
            # 重新排序 full_detail（加成後重算）
            for d in full_detail:
                d['score'] = score_map[d['num']]
                if freq_counter.get(d['num'], 0) >= 2:
                    d['reasons'] += f" | 🔥近{freq_window}期高頻({freq_counter[d['num']]}次)"

        full_detail = sorted(full_detail, key=lambda x: x['score'], reverse=True)
        full_pool = [d['num'] for d in full_detail]

        l_pairs, l_triplets, c_pairs, c_triplets = self._get_synergy_data(target_idx, target_date)
        
        combos = self._build_v99_combinations(full_pool, score_map, 
                    [p for p, _ in l_pairs.most_common(30)], 
                    [p for p, _ in l_triplets.most_common(15)], 
                    [p for p, _ in c_pairs.most_common(30)], 
                    [p for p, _ in c_triplets.most_common(15)], 
                    target_ma_sum, sets)
        
        return full_pool, full_detail, full_pool[:6], combos

    def _build_v99_combinations(self, pool, score_map, l_pairs, l_triplets, c_pairs, c_triplets, target_ma_sum, sets):
        final_combos = []
        class ComboResult:
            def __init__(self, combo, score, reasons):
                self.combo = sorted(combo)
                self.score = score
                self.reasons = reasons
                self.rank = 0

        unassigned_nums = list(range(1, 50))
        unassigned_nums.sort(key=lambda x: score_map.get(x, 0), reverse=True)
        
        # 💡 修正 1：提前計算連號對，避免跟定膽號碼衝突
        best_consec_score = -999
        consec_anchor = None
        for n in range(1, 49):
            pair_score = score_map.get(n, 0) + score_map.get(n+1, 0)
            if pair_score > best_consec_score:
                best_consec_score = pair_score
                consec_anchor = (n, n+1)

        # 💡 修正 2：定膽產生時，排除最強的連號對，保護純粹高分號碼的品質
        # ── 定膽多樣化：前4名輪流配對，覆蓋更多高分號碼 ──
        possible_anchors = [n for n in unassigned_nums[:8] if consec_anchor is None or n not in consec_anchor]
        if len(possible_anchors) >= 4:
            attack_anchor_pairs = [
                (possible_anchors[0], possible_anchors[1]),
                (possible_anchors[0], possible_anchors[2]),
                (possible_anchors[1], possible_anchors[2]),
                (possible_anchors[0], possible_anchors[3]),
            ]
        else:
            attack_anchor_pairs = [(possible_anchors[0], possible_anchors[1])] * 4

        attack_sets = 4    # 維持4組高品質定膽
        defend_sets = 3    # 維持3組防禦
        elite_sets  = 2    # 額外2組精選(rank7+，避免重複)
        rem_sets = sets - attack_sets - defend_sets - elite_sets

        for i in range(attack_sets):
            anchors = list(attack_anchor_pairs[i])
            for attempts in range(2000):
                candidate = list(anchors)
                reasons = [f"🎯定膽({anchors[0]},{anchors[1]})"]

                if random.random() < 0.8:
                    top_fill = [n for n in unassigned_nums if n not in candidate]
                    for n in top_fill[:4]:
                        if len(candidate) < 6: candidate.append(n)
                    reasons.append("⚡高分填補")
                else:
                    is_triplet = random.random() < 0.5
                    if is_triplet:
                        t_pool = c_triplets if c_triplets and random.random() < 0.5 else l_triplets
                        if t_pool:
                            chosen = random.choice(t_pool[:15])
                            for x in chosen:
                                if x not in candidate: candidate.append(x)
                            reasons.append("🌟三星連動")
                    else:
                        p_pool = c_pairs if c_pairs and random.random() < 0.5 else l_pairs
                        if p_pool:
                            chosen = random.choice(p_pool[:15])
                            for x in chosen:
                                if x not in candidate: candidate.append(x)
                            reasons.append("✨雙星連動")
                    pool_unassigned = [n for n in unassigned_nums if n not in candidate]
                    if pool_unassigned and len(candidate) < 6:
                        taken = random.sample(pool_unassigned[:15], min(6-len(candidate), len(pool_unassigned[:15])))
                        candidate.extend(taken)

                while len(candidate) < 6:
                    fill = random.choice(pool[:25])
                    if fill not in candidate: candidate.append(fill)

                if len(candidate) > 6: candidate = candidate[:6]
                candidate.sort()

                if attempts < 1000:
                    if abs(sum(candidate) - target_ma_sum) > 55: continue
                    zones = [1 if n <= 16 else 2 if n <= 33 else 3 for n in candidate]
                    if len(set(zones)) < 2: continue
                    if zones.count(1) < 1: continue
                    if zones.count(3) >= 4: continue
                    odds = sum(1 for n in candidate if n % 2 != 0)
                    if odds in [0, 1, 6]: continue

                for n in candidate:
                    if n in unassigned_nums: unassigned_nums.remove(n)
                c_score = sum(score_map[n] for n in candidate)
                final_combos.append(ComboResult(candidate, c_score, reasons))
                break

        # 階段二：經典/連號防禦組
        # ----------------------------------------------------
        for i in range(defend_sets):
            for attempts in range(2000):
                candidate = []
                
                # 💡 修正 3：將連號防禦組移到防禦組的最後一組，不搶高分名次
                if i == defend_sets - 1:
                    reasons = ["🛡️連號防禦"]
                    if consec_anchor:
                        candidate.extend(list(consec_anchor))
                    take_k = random.choice([2, 3])
                else:
                    reasons = ["🛡️經典防禦"]
                    take_k = random.choice([3, 4])
                    
                pool_unassigned = [n for n in unassigned_nums if n not in candidate]
                if pool_unassigned:
                    taken = random.sample(pool_unassigned[:12], min(take_k, len(pool_unassigned[:12])))
                    candidate.extend(taken)

                while len(candidate) < 6:
                    fill = random.choice(pool[:30])
                    if fill not in candidate: candidate.append(fill)
                        
                candidate.sort()
                
                if attempts < 1000:
                    if abs(sum(candidate) - target_ma_sum) > 55: continue
                    zones = [1 if n <= 16 else 2 if n <= 33 else 3 for n in candidate]
                    if len(set(zones)) < 2: continue
                    if zones.count(1) < 1: continue  
                    odds = sum(1 for n in candidate if n % 2 != 0)
                    if odds in [0, 6]: continue
                
                for n in candidate:
                    if n in unassigned_nums: unassigned_nums.remove(n)
                c_score = sum(score_map[n] for n in candidate)
                final_combos.append(ComboResult(candidate, c_score, reasons))
                break

        # ----------------------------------------------------
        # 階段三：精華重組
        # ----------------------------------------------------
        for i in range(rem_sets):
            for attempts in range(2000):
                candidate = []
                reasons = ["💡精華重組"]
                
                chunk_size = min(len(unassigned_nums), max(1, len(unassigned_nums) // (rem_sets - i) + 1))
                chunk_size = min(chunk_size, 6)
                
                if unassigned_nums:
                    taken = random.sample(unassigned_nums[:chunk_size+2], min(chunk_size, len(unassigned_nums)))
                    candidate.extend(taken)
                
                if len(candidate) > 6: candidate = candidate[:6]
                
                while len(candidate) < 6:
                    fill = random.choice(pool[:25])
                    if fill not in candidate: candidate.append(fill)
                
                candidate.sort()
                
                if attempts < 1000:
                    if abs(sum(candidate) - target_ma_sum) > 55: continue
                    zones = [1 if n <= 16 else 2 if n <= 33 else 3 for n in candidate]
                    if len(set(zones)) < 2: continue
                    if zones.count(1) < 1: continue  
                
                for n in candidate:
                    if n in unassigned_nums: unassigned_nums.remove(n)
                c_score = sum(score_map[n] for n in candidate)
                final_combos.append(ComboResult(candidate, c_score, reasons))
                break

        # ─── 階段四：⭐ 差異化精選組 ───
        top_by_score = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
        existing = {tuple(sorted(fc.combo)) for fc in final_combos}
        for ei in range(elite_sets):
            start = 6 + ei * 6   # 精選1:rank7~12, 精選2:rank13~18
            e_cand = sorted([n for n, _ in top_by_score[start:start+6]])
            shift = 0
            while tuple(e_cand) in existing and shift < 10:
                shift += 2
                e_cand = sorted([n for n, _ in top_by_score[start+shift:start+shift+6]])
            zones = set(1 if n<=16 else 2 if n<=33 else 3 for n in e_cand)
            if len(zones) < 2:
                for n, _ in top_by_score:
                    nz = 1 if n<=16 else 2 if n<=33 else 3
                    if nz not in zones and n not in e_cand:
                        e_cand[-1] = n; e_cand.sort(); break
            existing.add(tuple(e_cand))
            e_score = sum(score_map[n] for n in e_cand)
            final_combos.append(ComboResult(e_cand, e_score, [f"⭐精選Rank{start+1}~{start+6}"]))

        # 絕對防漏機制
        while unassigned_nums:
            missing_num = unassigned_nums.pop(0)
            final_combos.sort(key=lambda x: x.score) 
            replaced = False
            for c in final_combos:
                for j in range(6):
                    curr = c.combo[j]
                    if sum(1 for fc in final_combos if curr in fc.combo) > 1 and curr not in anchors: 
                        c.combo[j] = missing_num
                        c.combo.sort()
                        c.score = sum(score_map.get(n,0) for n in c.combo)
                        replaced = True
                        break
                if replaced: break
            if not replaced:
                final_combos[0].combo[0] = missing_num
                final_combos[0].combo.sort()

        final_combos = sorted(final_combos, key=lambda x: x.score, reverse=True)
        for i, c in enumerate(final_combos): 
            c.rank = i + 1
            
        return final_combos

    def backtest(self, sets=12, last_n_periods=None, custom_start_idx=None):
        df = self.df_lotto
        total_len = len(df)
        has_special = 'special' in df.columns

        if last_n_periods is None or last_n_periods <= 0: start_idx = 30  
        else: start_idx = max(30, total_len - last_n_periods)
        test_count = total_len - start_idx
        
        print(f"\n🚀 啟動 V10.2 十二組差異化精選版 回測... (本次將回測最近 {test_count} 期)")
        rows = []
        for target_idx in range(start_idx, total_len):
            row_data   = df.iloc[target_idx]
            actual_nums = {int(float(row_data[f'n{i}'])) for i in range(1, 7)}
            actual_sp   = int(float(row_data['special'])) if has_special and pd.notna(row_data.get('special')) else None

            _, _, _, combos = self.generate(target_idx, sets=sets, custom_start_idx=custom_start_idx)

            # 主號命中（6顆）
            hits_main = [len(set(c.combo) & actual_nums) for c in combos]

            # 6+1 命中：主號命中數 + 特別號是否在該注裡（最多+1）
            hits_plus = []
            for c, h in zip(combos, hits_main):
                sp_bonus = 1 if (actual_sp is not None and actual_sp in set(c.combo)) else 0
                hits_plus.append(h + sp_bonus)

            rows.append({
                "period":          int(row_data['period']),
                "actual":          " ".join(f"{n:02d}" for n in sorted(actual_nums)),
                "actual_special":  f"{actual_sp:02d}" if actual_sp is not None else "--",
                # 主號統計
                "best_hit":        max(hits_main) if hits_main else 0,
                "top1_hit":        hits_main[0] if hits_main else 0,
                # 6+1 統計（主號+特別號）
                "best_hit_plus":   max(hits_plus) if hits_plus else 0,
                "top1_hit_plus":   hits_plus[0] if hits_plus else 0,
            })
            completed = target_idx - start_idx + 1
            if completed % 10 == 0 or completed == test_count:
                print(f"進度：已完成 {completed} / {test_count} 期...")
        return rows
