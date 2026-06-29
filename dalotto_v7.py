import os, glob, unicodedata, pandas as pd
from common_loader import load_history
from hit_engine import HitOptimizedEngine
from v7_engine import V7StructureEngine

def print_files(files):
    for f in files:
        print(" -", os.path.basename(f))

def load_539_history_smart():
    """ 智慧路徑偵測：相容 data/imports_539/ 與 根目錄下的539歷史檔案 """
    possible_paths = [
        os.path.join("data", "imports_539", "*.csv"),
        "*539*.csv"
    ]
    files = []
    for pattern in possible_paths:
        matched = glob.glob(pattern)
        if matched: files.extend(matched)
    if not files: return pd.DataFrame(), []
    
    df_list = []
    for f in files:
        for enc in ['utf-8-sig', 'cp950', 'big5', 'utf-8']:
            try:
                df_raw = pd.read_csv(f, header=None, encoding=enc, on_bad_lines='skip')
                break
            except: continue
        if df_raw is None or df_raw.empty: continue
        header_idx = -1
        for i in range(min(15, len(df_raw))):
            row_str = "".join(map(str, df_raw.iloc[i].values)).lower()
            if ('日' in row_str or 'date' in row_str) and ('號' in row_str or '1' in row_str):
                header_idx = i; break
        if header_idx != -1:
            df_raw.columns = df_raw.iloc[header_idx].astype(str)
            df = df_raw.iloc[header_idx+1:].copy()
            clean = pd.DataFrame()
            for col in df.columns:
                c = str(col).lower()
                if '日' in c or 'date' in c: clean['date'] = df[col]
                elif '期' in c or 'period' in c: clean['period'] = df[col]
                elif '1' in c: clean['n1'] = df[col]
                elif '2' in c: clean['n2'] = df[col]
                elif '3' in c: clean['n3'] = df[col]
                elif '4' in c: clean['n4'] = df[col]
                elif '5' in c: clean['n5'] = df[col]
            if all(req in clean.columns for req in ['date', 'n1', 'n2', 'n3', 'n4', 'n5']):
                clean['date'] = pd.to_datetime(clean['date'], errors='coerce')
                for n in ['n1', 'n2', 'n3', 'n4', 'n5']:
                    clean[n] = pd.to_numeric(clean[n], errors='coerce')
                clean = clean.dropna(subset=['date', 'n1', 'n2', 'n3', 'n4', 'n5'])
                df_list.append(clean)
    if not df_list: return pd.DataFrame(), []
    return pd.concat(df_list).sort_values('date').reset_index(drop=True), files

def mode_predict(df, engine):
    sets = 12 
    user_input = input("輸入目標期別 (按 Enter 直接預測最新一期)：").strip()
    if user_input.isdigit():
        period = int(user_input)
        idx_map = {int(df.iloc[i]['period']): i for i in range(len(df))}
        target_idx = idx_map.get(period, len(df))
    else:
        target_idx = len(df)
        
    bg_start_idx = 0  # 使用全部歷史資料
    target_period = int(df.iloc[target_idx]['period']) if target_idx < len(df) else int(df.iloc[-1]['period']) + 1
    
    _, _, _, combos = engine.generate(target_idx, sets=sets, custom_start_idx=bg_start_idx)
    
    bg_periods = df.iloc[bg_start_idx:target_idx]['period'].tolist()
    if bg_periods: print(f"\n參考背景期數：{bg_periods[0]} ~ {bg_periods[-1]}")
    print(f"預測目標期：{target_period}")
    print("\n📝 預測清單 (V10.2 十二組擴展版: 總和引力標靶 + 皇牌定膽)：")
    rows = []
    all_selected_nums = set()
    for c in combos:
        all_selected_nums.update(c.combo)
        line = " ".join(f"{n:02d}" for n in c.combo)
        reason = " ; ".join(c.reasons)
        print(f"{c.rank:02d}. {line} | score={c.score:.4f} | {reason}")
        rows.append({"rank":c.rank, "combo":line, "score":c.score, "reason":reason})
    
    missing = set(range(1, 50)) - all_selected_nums
    if not missing: print("\n✅ 系統檢測報告：1~49 號碼已完美全數涵蓋！無遺漏！")
    else: print(f"\n⚠️ 系統檢測報告：發生意外，遺漏了號碼 {missing}")

    # 特別號候選輸出（實際呼叫引擎的 SpecialNumberEngine 計算）
    special_candidates = []
    if hasattr(engine, 'special_engine'):
        special_candidates = engine.special_engine.get_special_predictions(target_idx, top_k=3)
    if special_candidates:
        special_str = "  ".join(f"{n:02d}" for n in special_candidates)
        print(f"\n🎱 特別號候選（Top 3，近30期頻率加權）：{special_str}")
        print("   └ 第1位優先參考；註：經回測特別號預測準度接近隨機，僅供參考、勿過度依賴")
        
    os.makedirs("output", exist_ok=True)
    pd.DataFrame(rows).to_csv(f"output/predict_{target_period}_{sets}sets.csv", index=False, encoding="utf-8-sig")
    print(f"✅ 已同步輸出至：output/predict_{target_period}_{sets}sets.csv")

def mode_window(df, engine):
    idx_map = {int(df.iloc[i]['period']): i for i in range(len(df))}
    
    target_input = input("輸入【實際要對獎的目標期別】(例如 115000032)：").strip()
    if not target_input.isdigit() or int(target_input) not in idx_map:
        return print("⚠️ 錯誤：找不到對獎目標期別")
    
    target_idx = idx_map[int(target_input)]
    bg_start_idx = 0  # 使用全部歷史資料

    # 統一顯示格式：顯示「起點 ~ 終點」（與模式1一致）
    bg_periods = df.iloc[bg_start_idx:target_idx]['period'].tolist()
    if bg_periods:
        print(f"   => 系統已自動鎖定最佳波形參考區間：{bg_periods[0]} ~ {bg_periods[-1]}")
    
    _, _, _, combos = engine.generate(target_idx, sets=12, custom_start_idx=bg_start_idx)
    actual = {int(df.iloc[target_idx][f'n{i}']) for i in range(1, 7)}
    
    print(f"\n🎯 第 {int(df.iloc[target_idx]['period'])} 期 實際開獎：{' '.join(f'{n:02d}' for n in sorted(actual))}")

    actual_sp = None
    if 'special' in df.columns and pd.notna(df.iloc[target_idx].get('special')):
        actual_sp = int(float(df.iloc[target_idx]['special']))
        print(f"🎱 實際特別號：{actual_sp:02d}")

    for c in combos:
        main_hit  = len(set(c.combo) & actual)
        sp_hit    = 1 if (actual_sp is not None and actual_sp in set(c.combo)) else 0
        total_hit = main_hit + sp_hit
        reason    = c.reasons[0] if c.reasons else ""
        sp_tag    = " +特別號✅" if sp_hit else ""
        print(f"{c.rank:02d}. {' '.join(f'{n:02d}' for n in c.combo)} | 主號命中 {main_hit} 顆{sp_tag} | 合計 {total_hit} 顆 | {reason}")

def mode_backtest(df, engine):
    sets = 12
    periods_input = input("輸入要回測的最近期數 (直接按 Enter 則回測全部)：").strip()
    last_n_periods = int(periods_input) if periods_input.isdigit() else None
    
    rows = engine.backtest(sets=sets, last_n_periods=last_n_periods)
    out = pd.DataFrame(rows)
    os.makedirs("output", exist_ok=True)
    
    while True:
        try:
            out.to_csv("output/backtest_summary.csv", index=False, encoding="utf-8-sig")
            break
        except: input("\n⚠️ 請關閉 backtest_summary.csv 後按 Enter 重試...")

    has_plus = "best_hit_plus" in out.columns

    metrics = {
        "total_windows":           len(out),
        "best_hit_3plus_windows":  int((out["best_hit"] >= 3).sum()) if len(out) else 0,
        "best_hit_4plus_windows":  int((out["best_hit"] >= 4).sum()) if len(out) else 0,
        "top1_hit_3plus_windows":  int((out["top1_hit"] >= 3).sum()) if len(out) else 0,
        "avg_best_hit":            round(float(out["best_hit"].mean()), 4) if len(out) else 0.0,
    }

    if has_plus:
        metrics.update({
            "plus_best_hit_3plus_windows": int((out["best_hit_plus"] >= 3).sum()),
            "plus_best_hit_4plus_windows": int((out["best_hit_plus"] >= 4).sum()),
            "plus_top1_hit_3plus_windows": int((out["top1_hit_plus"] >= 3).sum()),
            "plus_avg_best_hit":           round(float(out["best_hit_plus"].mean()), 4),
        })

    while True:
        try:
            pd.DataFrame([metrics]).to_csv("output/backtest_metrics.csv", index=False, encoding="utf-8-sig")
            break
        except: input("\n⚠️ 請關閉 backtest_metrics.csv 後按 Enter 重試...")

    print("\n✅ 回測完成！")
    print("\n【📊 主號統計（只算 6 顆主號）】")
    main_keys = ["total_windows","best_hit_3plus_windows","best_hit_4plus_windows",
                 "top1_hit_3plus_windows","avg_best_hit"]
    print(pd.DataFrame([{k: metrics[k] for k in main_keys}]).to_string(index=False))

    if has_plus:
        print("\n【🎱 6+1 統計（主號 + 特別號合計）】")
        plus_keys = ["total_windows","plus_best_hit_3plus_windows","plus_best_hit_4plus_windows",
                     "plus_top1_hit_3plus_windows","plus_avg_best_hit"]
        print(pd.DataFrame([{k: metrics[k] for k in plus_keys}]).to_string(index=False))

        helped    = (out["best_hit_plus"] > out["best_hit"]).sum()
        diff_3plus = metrics["plus_best_hit_3plus_windows"] - metrics["best_hit_3plus_windows"]
        diff_4plus = metrics["plus_best_hit_4plus_windows"] - metrics["best_hit_4plus_windows"]
        diff_avg   = round(metrics["plus_avg_best_hit"] - metrics["avg_best_hit"], 4)
        pct        = round(helped / len(out) * 100, 1) if len(out) else 0
        print(f"\n【📈 特別號加入後的提升效益】")
        print(f"  特別號提升命中的期數：{helped}/{len(out)} 期 ({pct}%)")
        print(f"  3+ 命中期數：{metrics['best_hit_3plus_windows']} → {metrics['plus_best_hit_3plus_windows']} (增加 {diff_3plus:+d} 期)")
        print(f"  4+ 命中期數：{metrics['best_hit_4plus_windows']} → {metrics['plus_best_hit_4plus_windows']} (增加 {diff_4plus:+d} 期)")
        print(f"  平均最佳命中：{metrics['avg_best_hit']} → {metrics['plus_avg_best_hit']} ({diff_avg:+.4f})")
        if diff_3plus > 0 or diff_avg > 0:
            print(f"  ✅ 特別號有助提升命中，值得加購！")
        else:
            print(f"  ⚠️  特別號提升效益不明顯，可評估是否加購")

def _disp_w(s):
    """計算字串顯示寬度（全形/CJK 算 2，半形算 1），供終端機表格對齊用"""
    return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in str(s))

def _pad(s, width, align='left'):
    """依顯示寬度補空白：align='left' 靠左、'right' 靠右"""
    s = str(s)
    gap = max(0, width - _disp_w(s))
    return (s + ' ' * gap) if align == 'left' else (' ' * gap + s)

def mode_grid15(df, engine):
    """模式4：近 N 期『逐組命中對照矩陣』(預設15期)
       橫列 = 組1~組12，縱欄 = 近 N 期期號，格值 = 該組（主號命中 + 特別號；中特別號直接 +1）。
       條件與模式2『對答案』完全一致 (custom_start_idx=0，使用全部歷史)，可逐期互相核對。"""
    sets = 12
    user_input = input("輸入要回測的最近期數 (直接按 Enter 預設 15 期)：").strip()
    last_n = int(user_input) if (user_input.isdigit() and int(user_input) > 0) else 15

    total = len(df)
    has_special = 'special' in df.columns
    start_idx = max(30, total - last_n)           # 至少保留前30期作背景
    target_indices = list(range(start_idx, total))
    n_periods = len(target_indices)
    if n_periods == 0:
        return print("⚠️ 資料不足，無法回測。")
    if n_periods < last_n:
        print(f"⚠️ 可回測期數不足 {last_n} 期，實際回測 {n_periods} 期。")

    print(f"\n🚀 啟動近 {n_periods} 期逐組命中矩陣回測（與『對答案』同條件：使用全部歷史）...")

    periods, actuals = [], []                      # actuals[col] = (sorted主號list, 特別號or None)
    grid = [[(0, 0)] * n_periods for _ in range(sets)]   # grid[組][期] = (主號命中, 特別號命中0/1)
    cache = []                                      # cache[col] = (full_pool, [combo號碼list...], 預測特別號Top1)

    for col, target_idx in enumerate(target_indices):
        row = df.iloc[target_idx]
        actual_nums = {int(float(row[f'n{i}'])) for i in range(1, 7)}
        actual_sp = int(float(row['special'])) if has_special and pd.notna(row.get('special')) else None
        periods.append(int(row['period']))
        actuals.append((sorted(actual_nums), actual_sp))

        full_pool, _, _, combos = engine.generate(target_idx, sets=sets, custom_start_idx=0)
        for r in range(sets):
            if r < len(combos):
                cb = set(combos[r].combo)
                mh = len(cb & actual_nums)
                sp = 1 if (actual_sp is not None and actual_sp in cb) else 0
                grid[r][col] = (mh, sp)
        sp_pred = None
        if has_special and hasattr(engine, 'special_engine'):
            preds = engine.special_engine.get_special_predictions(target_idx, top_k=1)
            sp_pred = preds[0] if preds else None
        cache.append((list(full_pool), [list(c.combo) for c in combos], sp_pred))
        print(f"進度：{col + 1}/{n_periods} 期（第 {periods[-1]} 期）完成")

    # ── 排版參數：列=期號、欄=組01~組12 ──
    LABEL_W = max(11, max(_disp_w(str(p)) for p in periods) + 2)   # 列首放完整期號
    col_w = 5                                                      # 每個組欄寬

    # ── 期號對照（完整期號 → 實際開獎）──
    print("\n【期號對照（期號 → 實際開獎）】")
    for p, (an, sp) in zip(periods, actuals):
        sp_s = f"  特:{sp:02d}" if sp is not None else ""
        print(f"  {p} → {' '.join(f'{n:02d}' for n in an)}{sp_s}")

    # ── 矩陣本體（橫排=組01~組12，直排=各期期號）──
    print("\n【逐組命中矩陣（數字 = 主號命中 + 特別號；中特別號直接 +1）】")
    header = _pad("期號＼組", LABEL_W) + "".join(_pad(f"組{r + 1:02d}", col_w, 'right') for r in range(sets)) + _pad("最佳", col_w, 'right')
    print(header)
    print("-" * _disp_w(header))
    for col in range(n_periods):                                   # 每一列 = 一期
        cells = []
        for r in range(sets):
            mh, sp = grid[r][col]
            cells.append(_pad(str(mh + sp), col_w, 'right'))        # 中特別號 +1
        best = max(grid[r][col][0] + grid[r][col][1] for r in range(sets))
        print(_pad(str(periods[col]), LABEL_W) + "".join(cells) + _pad(str(best), col_w, 'right'))
    print("-" * _disp_w(header))
    # 底列：各組 15 期命中合計（含特別號 +1）
    sum_cells = [_pad(str(sum(grid[r][col][0] + grid[r][col][1] for col in range(n_periods))), col_w, 'right') for r in range(sets)]
    print(_pad("該組合計", LABEL_W) + "".join(sum_cells))

    # ── 摘要 ──
    flat = [grid[r][col][0] + grid[r][col][1] for r in range(sets) for col in range(n_periods)]
    print(f"\n📊 摘要：{n_periods} 期 × {sets} 組 = {len(flat)} 注（含特別號+1）；"
          f"最高單注 {max(flat)}；達3+ {sum(1 for x in flat if x >= 3)} 注、"
          f"達4+ {sum(1 for x in flat if x >= 4)} 注、達5+ {sum(1 for x in flat if x >= 5)} 注。")

    # ── 輸出 CSV（APP 可直接讀取：列=期號、欄=組01~組12，數字含特別號+1）──
    os.makedirs("output", exist_ok=True)
    out_rows = []
    for col in range(n_periods):                                   # 每一列 = 一期
        an, sp_act = actuals[col]
        d = {"期號": periods[col]}
        for r in range(sets):
            mh, sp = grid[r][col]
            d[f"組{r + 1:02d}"] = mh + sp                           # 中特別號 +1
        d["最佳"] = max(grid[r][col][0] + grid[r][col][1] for r in range(sets))
        d["實際開獎"] = " ".join(f"{n:02d}" for n in an) + (f"(特{sp_act:02d})" if sp_act is not None else "")
        out_rows.append(d)
    total_row = {"期號": "該組合計"}
    for r in range(sets):
        total_row[f"組{r + 1:02d}"] = sum(grid[r][col][0] + grid[r][col][1] for col in range(n_periods))
    total_row["最佳"] = ""
    total_row["實際開獎"] = ""
    out_rows.append(total_row)

    out_path = f"output/grid_backtest_{n_periods}periods.csv"
    while True:
        try:
            pd.DataFrame(out_rows).to_csv(out_path, index=False, encoding="utf-8-sig")
            break
        except PermissionError:
            input(f"\n⚠️ 請關閉 {out_path} 後按 Enter 重試...")
    print(f"\n✅ 已輸出矩陣至：{out_path}")

    # ══════════════════════════════════════════════
    # 可選：普獎攻擊 A/B 對照
    #   A版 = 原始12組
    #   B版 = 將分數最低的 K 組換成「預測特別號(事前) + 高分池號碼」攻擊組
    #   兩版都用『真實特別號』驗證，無事後作弊。
    #   大樂透普獎 = 中3主號，或 中2主號+特別號。特別號只能把『恰中2主號』救成普獎。
    # ══════════════════════════════════════════════
    if not has_special:
        return
    ans = input("\n要不要同時跑【普獎攻擊版】A/B 對照？(輸入 y 執行，直接 Enter 略過)：").strip().lower()
    if ans != 'y':
        return
    k_input = input("要用幾組來攻普獎？(直接 Enter 預設 2 組)：").strip()
    K = int(k_input) if (k_input.isdigit() and 1 <= int(k_input) <= sets) else 2

    def is_win(mh, has_sp):       # 是否中任何獎（含普獎）
        return mh >= 3 or (mh == 2 and has_sp)
    def is_pumi_by_sp(mh, has_sp):  # 是否為「2主號+特別號」這種被特別號救起來的普獎
        return mh == 2 and has_sp

    print(f"\n🎯 普獎攻擊 A/B 對照（B = 最低分 {K} 組換成『預測特別號＋高分池』）")
    hdr = _pad("期號", 12) + _pad("預測特", 8) + _pad("實際特", 8) + _pad("A中獎", 7) + _pad("B中獎", 7) + _pad("A(2+特)", 9) + _pad("B(2+特)", 9)
    print(hdr); print("-" * _disp_w(hdr))

    tot_a_win = tot_b_win = tot_a_pumi = tot_b_pumi = sp_top1_hit = 0
    for col in range(n_periods):
        actual_nums, actual_sp = set(actuals[col][0]), actuals[col][1]
        full_pool, combo_lists, sp_pred = cache[col]
        if actual_sp is not None and sp_pred == actual_sp:
            sp_top1_hit += 1

        # A版：原始12組
        a_win = a_pumi = 0
        for cb in combo_lists:
            mh = len(set(cb) & actual_nums)
            hs = actual_sp is not None and actual_sp in set(cb)
            a_win += is_win(mh, hs); a_pumi += is_pumi_by_sp(mh, hs)

        # B版：保留前 sets-K 組，最後 K 組換成攻擊組
        b_combos = [list(cb) for cb in combo_lists[:sets - K]]
        if sp_pred is not None:
            pool_excl = [n for n in full_pool if n != sp_pred]
            for j in range(K):
                fill = pool_excl[j * 5:j * 5 + 5]
                if len(fill) < 5:                      # 池不夠就補
                    fill += [n for n in pool_excl if n not in fill][:5 - len(fill)]
                b_combos.append(sorted(set([sp_pred] + fill)))
        else:
            b_combos += [list(cb) for cb in combo_lists[sets - K:]]  # 無預測值則維持原組

        b_win = b_pumi = 0
        for cb in b_combos:
            mh = len(set(cb) & actual_nums)
            hs = actual_sp is not None and actual_sp in set(cb)
            b_win += is_win(mh, hs); b_pumi += is_pumi_by_sp(mh, hs)

        tot_a_win += a_win; tot_b_win += b_win; tot_a_pumi += a_pumi; tot_b_pumi += b_pumi
        sp_p = f"{sp_pred:02d}" if sp_pred is not None else "--"
        sp_a = f"{actual_sp:02d}" if actual_sp is not None else "--"
        print(_pad(str(periods[col]), 12) + _pad(sp_p, 8) + _pad(sp_a, 8) +
              _pad(str(a_win), 7) + _pad(str(b_win), 7) + _pad(str(a_pumi), 9) + _pad(str(b_pumi), 9))

    print("-" * _disp_w(hdr))
    print("\n【📈 A/B 總結（皆以真實特別號驗證）】")
    print(f"  預測特別號(Top1) 實際命中：{sp_top1_hit}/{n_periods} 期 "
          f"({sp_top1_hit / n_periods * 100:.1f}%；隨機基準 {100/49:.1f}%)")
    print(f"  任何中獎注數：A={tot_a_win} → B={tot_b_win}  (差異 {tot_b_win - tot_a_win:+d})")
    print(f"  其中『2主+特』普獎注數：A={tot_a_pumi} → B={tot_b_pumi}  (差異 {tot_b_pumi - tot_a_pumi:+d})")
    if tot_b_win > tot_a_win:
        print("  ✅ 本次樣本中，攻擊版總中獎注數較多——但這仍受特別號隨機性影響，換個區間可能翻盤。")
    elif tot_b_win == tot_a_win:
        print("  ➖ 本次樣本中，攻擊版與原版打平，沒有明顯效益。")
    else:
        print("  ⚠️ 本次樣本中，攻擊版反而較差（犧牲了2組主號覆蓋）。這正說明：靠預測特別號去湊普獎並不划算。")
    print("  📌 提醒：特別號每期獨立隨機，以上為真實回測、非保證；請勿據此加碼下注。")

def main():
    print("載入歷史資料中，請稍候...")
    # 智慧路徑：優先 data/imports，找不到就掃同資料夾
    import glob, os
    lotto_paths = ["data/imports"]
    if not glob.glob(os.path.join("data", "imports", "*.csv")):
        lotto_paths = ["."]   # 同資料夾
    df_lotto, files_lotto = load_history(lotto_paths)
    df_539, files_539 = load_539_history_smart()
    
    base_engine = HitOptimizedEngine(df_lotto)
    
    # 💡 V10.2：引擎只傳入大樂透與539，不使用外部威力彩資料
    v99_engine = V7StructureEngine(base_engine, df_lotto, df_539)
    
    os.system('cls' if os.name == 'nt' else 'clear')
    while True:
        print('==================================================')
        print('       大樂透 AI 預測系統 (V10.2 十二組擴展版)     ')
        print('==================================================')
        if not df_lotto.empty: print(f'📊 大樂透：共 {len(df_lotto)} 期')
        if not df_539.empty: print(f'📈 今彩539：共 {len(df_539)} 期 (跨彩種連動亮燈)')
        print('--------------------------------------------------')
        print(' 1. 直接預測 (總和引力標靶 + 皇牌定膽)')
        print(' 2. 歷史回測對答案')
        print(' 3. 系統極限壓力測試')
        print(' 4. 近15期逐組命中對照表 (回測矩陣)')
        print(' 5. 離開系統')
        print('==================================================')
        choice = input('請選擇模式 (1-5): ').strip()

        if choice == '1': mode_predict(df_lotto, v99_engine)
        elif choice == '2': mode_window(df_lotto, v99_engine)
        elif choice == '3': mode_backtest(df_lotto, v99_engine)
        elif choice == '4': mode_grid15(df_lotto, v99_engine)
        elif choice == '5': break
        print('\n' + '-'*50 + '\n')

if __name__ == "__main__": 
    main()