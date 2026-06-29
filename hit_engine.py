import itertools, collections, statistics
from dataclasses import dataclass
from common_loader import MAIN_COLS

LOW = range(1,17)
MID = range(17,34)
HIGH = range(34,50)

@dataclass
class ComboResult:
    rank:int
    combo:tuple
    score:float
    reasons:list

class HitOptimizedEngine:
    def __init__(self, df):
        self.df = df.copy()

    def _window(self, end_idx, size=20):
        start = max(0, end_idx-size)
        return self.df.iloc[start:end_idx].copy()

    def _main_sets(self, part):
        return [set(int(row[c]) for c in MAIN_COLS) for _,row in part.iterrows()]

    def build_pool(self, end_idx):
        hist20 = self._window(end_idx,20)
        hist10 = self._window(end_idx,10)
        hist2 = self._window(end_idx,2)
        prev1 = self._window(end_idx,1)

        last_seen = {}
        for i in range(end_idx-1, -1, -1):
            nums = set(int(self.df.iloc[i][c]) for c in MAIN_COLS)
            for n in nums:
                if n not in last_seen:
                    last_seen[n] = end_idx - i

        sets10 = self._main_sets(hist10)
        sets20 = self._main_sets(hist20)
        freq10 = collections.Counter()
        freq20 = collections.Counter()
        for s in sets10: freq10.update(s)
        for s in sets20: freq20.update(s)

        recent2 = set()
        for s in self._main_sets(hist2): recent2 |= s
        prevnums = self._main_sets(prev1)[0] if len(prev1) else set()

        similar_next = collections.Counter()
        if end_idx >= 21:
            target_vec = [freq10.get(i,0) for i in range(1,50)]
            sims = []
            for j in range(10, end_idx-1):
                part = self.df.iloc[j-10:j]
                nxt = self.df.iloc[j]
                c = collections.Counter()
                for s in self._main_sets(part): c.update(s)
                vec = [c.get(i,0) for i in range(1,50)]
                dist = sum(abs(a-b) for a,b in zip(target_vec, vec))
                sims.append((dist, nxt))
            sims.sort(key=lambda x:x[0])
            for _, nxt in sims[:5]:
                for c in MAIN_COLS:
                    similar_next[int(nxt[c])] += 1

        pair_counter = collections.Counter()
        trip_counter = collections.Counter()
        for s in sets20:
            for a,b in itertools.combinations(sorted(s),2): pair_counter[(a,b)] += 1
            for tri in itertools.combinations(sorted(s),3): trip_counter[tri] += 1

        pool_scores, pool_reasons = {}, {}
        for n in range(1,50):
            score = 0.0
            reasons = []
            if freq10[n] > 0:
                score += 1.8; reasons.append(f"前10期出現{freq10[n]}次 +1.8")
            if n not in recent2:
                score += 1.2; reasons.append("近2期未連續出現 +1.2")
            omit = last_seen.get(n, 999)
            if omit >= 10:
                score += 1.6; reasons.append(f"遺漏{omit}期 +1.6")
            if omit >= 20:
                score += 2.0; reasons.append("遺漏達20期級別 +2.0")
            if freq10[n] >= 4:
                score -= 1.7; reasons.append(f"近10期過熱{freq10[n]}次 -1.7")
            if any(abs(n-p) in (1,2) for p in prevnums):
                score += 1.0; reasons.append("前一期±1/±2關聯 +1.0")
            tail_ct = sum(1 for x in prevnums if x % 10 == n % 10)
            if tail_ct:
                bonus = 0.5*tail_ct
                score += bonus; reasons.append(f"與前一期同尾{tail_ct}個 +{bonus:.1f}")
            if similar_next[n]:
                bonus = 0.8*similar_next[n]
                score += bonus; reasons.append(f"相似盤面支持{similar_next[n]}次 +{bonus:.1f}")
            if freq20[n]:
                bonus = 0.18*freq20[n]
                score += bonus; reasons.append(f"近20期頻率{freq20[n]}次 +{bonus:.2f}")
            pool_scores[n] = score
            pool_reasons[n] = reasons

        ranked = sorted(pool_scores.items(), key=lambda x:(-x[1], x[0]))
        pool = [n for n,_ in ranked[:16]]
        detail = [{"num":n, "score":round(pool_scores[n],4), "reasons":" | ".join(pool_reasons[n])} for n in pool]
        return pool, detail, pair_counter, trip_counter, freq20

    def _zone_counts(self, combo):
        low = sum(1 for x in combo if x in LOW)
        mid = sum(1 for x in combo if x in MID)
        high = sum(1 for x in combo if x in HIGH)
        return low, mid, high

    def _combo_score(self, combo, core, pair_counter, trip_counter, recent_avg_sum, freq20):
        combo = tuple(sorted(combo))
        score = 0.0
        reasons = []
        core_hit = len(set(combo) & set(core))
        if core_hit >= 2:
            score += 3.0 + 0.6*(core_hit-2); reasons.append(f"核心號命中{core_hit}個")
        pair_score = sum(pair_counter.get(tuple(sorted(p)),0) for p in itertools.combinations(combo,2))
        trip_score = sum(trip_counter.get(tuple(sorted(t)),0) for t in itertools.combinations(combo,3))
        score += pair_score * 0.18; score += trip_score * 0.35
        reasons.append(f"pair={pair_score}"); reasons.append(f"triplet={trip_score}")
        low, mid, high = self._zone_counts(combo)
        zones_present = sum(1 for z in (low,mid,high) if z>0)
        if zones_present >= 2:
            score += 1.2; reasons.append("至少2區存在")
        if (low,mid,high) in [(2,2,2),(2,3,1),(1,3,2)]:
            score += 1.3; reasons.append(f"區間結構佳 {low}-{mid}-{high}")
        if low == 0 or high == 0:
            score -= 1.5; reasons.append("全偏單區懲罰")
        s = sum(combo)
        if abs(s - recent_avg_sum) <= 18:
            score += 1.2; reasons.append(f"總和貼近常模 {s}")
        elif abs(s - recent_avg_sum) <= 30:
            score += 0.5; reasons.append(f"總和可接受 {s}")
        else:
            score -= 0.8; reasons.append(f"總和偏離 {s}")
        odd = sum(1 for x in combo if x % 2 == 1)
        even = 6 - odd
        if (odd, even) in [(3,3),(4,2),(2,4)]:
            score += 1.0; reasons.append(f"奇偶比佳 {odd}:{even}")
        tails = [x%10 for x in combo]
        if max(collections.Counter(tails).values()) <= 2:
            score += 0.7; reasons.append("同尾不過度集中")
        else:
            score -= 1.0; reasons.append("同尾過度集中")
        consec = sum(1 for a,b in zip(combo, combo[1:]) if b-a == 1)
        if consec >= 1:
            score += 0.6; reasons.append(f"含連號{consec}段")
        gaps2 = sum(1 for a,b in itertools.combinations(combo,2) if abs(a-b) == 2)
        if gaps2 >= 1:
            score += 0.4; reasons.append(f"含間隔2配對{gaps2}個")
        score += sum(freq20[n] for n in combo) * 0.05
        return score, reasons

    def generate(self, end_idx, sets=10):
        hist20 = self._window(end_idx,20)
        pool, detail, pair_counter, trip_counter, freq20 = self.build_pool(end_idx)
        recent_avg_sum = statistics.mean(sum(int(row[c]) for c in MAIN_COLS) for _,row in hist20.iterrows()) if len(hist20) else 150
        core = [d["num"] for d in detail[:5]]
        candidates = []
        for combo in itertools.combinations(pool, 6):
            if len(set(combo) & set(core)) < 2:
                continue
            score, reasons = self._combo_score(combo, core, pair_counter, trip_counter, recent_avg_sum, freq20)
            candidates.append((score, combo, reasons))
        candidates.sort(key=lambda x:(-x[0], x[1]))
        chosen, covered = [], set()
        for score, combo, reasons in candidates:
            if any(len(set(combo)&set(c.combo)) > 3 for c in chosen):
                continue
            bonus = len(set(combo)-covered)*0.15
            chosen.append(ComboResult(rank=len(chosen)+1, combo=combo, score=round(score+bonus,4), reasons=reasons+[f"覆蓋增益={bonus:.2f}"]))
            covered |= set(combo)
            if len(chosen) >= sets:
                break
        if len(chosen) < sets:
            for score, combo, reasons in candidates:
                if any(combo == c.combo for c in chosen):
                    continue
                chosen.append(ComboResult(rank=len(chosen)+1, combo=combo, score=round(score,4), reasons=reasons))
                if len(chosen) >= sets:
                    break
        return pool, detail, core, chosen

    def backtest(self, sets=10):
        rows = []
        for end_idx in range(20, len(self.df)):
            target_period = int(self.df.iloc[end_idx]['period'])
            actual = set(int(self.df.iloc[end_idx][c]) for c in MAIN_COLS)
            pool, detail, core, combos = self.generate(end_idx, sets=sets)
            hit_list = [len(set(c.combo) & actual) for c in combos]
            rows.append({
                "target_period": target_period,
                "actual": " ".join(f"{n:02d}" for n in sorted(actual)),
                "best_hit": max(hit_list) if hit_list else 0,
                "count_hit_2plus": sum(1 for h in hit_list if h >= 2),
                "count_hit_3plus": sum(1 for h in hit_list if h >= 3),
                "top1_combo": " ".join(f"{n:02d}" for n in combos[0].combo) if combos else "",
                "top1_hit": hit_list[0] if hit_list else 0,
            })
        return rows
