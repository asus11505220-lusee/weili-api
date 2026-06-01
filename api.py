from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 👉 1. 新增這行：載入 CORS 套件
from datetime import datetime
# 匯入你原本的運算引擎 (檔名必須是 weili_v8_engine.py)
import weili_v8_engine as engine 

# 建立 FastAPI 應用程式
app = FastAPI(title="生肖威力生碼器 API")

# 👉 2. 新增這整段：對全世界發放通行證
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... (下面維持你原本寫好的路由跟邏輯) ...

# 建立一個路由 (當 APP 呼叫 /generate 網址時，就會執行這個函數)
@app.get("/generate")
def generate_zodiac_numbers():
    try:
        # 1. 載入歷史資料 (直接呼叫你原本寫好的函數)
        history_wl = engine.load_csv(engine.WEILI_CSV)
        history_539 = engine.load_csv(engine.C539_CSV)

        # 2. 取得最新日期與統計資料
        ref_date = history_wl[-1]['date_obj'] if history_wl else datetime.now()
        top_539_singles, bonds_539 = engine.get_539_chemical_bonds(history_539, ref_date)
        pair_stats, triplet_stats, z1_z2_pair_count, p5, p10, p15, p20, single_freq = engine.build_advanced_stats(history_wl, bonds_539)

        # 3. 執行 12 組蒙地卡羅運算 (這裡 mc_runs 設為 10，避免 API 算太久導致手機 APP 等到超時)
        zone1_combos = engine.generate_zone1_hedging_matrix(
            single_freq, pair_stats, triplet_stats, p5, p10, p15, p20, bonds_539, 
            mc_runs=10, history_wl=history_wl
        )
        
        # 4. 運算第二區 (聲波干涉)
        zone2_ordered, z2_scores = engine.assign_zone2_perfect_match(zone1_combos, z1_z2_pair_count, history_wl)

        # 5. 將結果與 12 生肖進行綁定，整理成 APP 看得懂的格式
        zodiacs = ['鼠', '牛', '虎', '兔', '龍', '蛇', '馬', '羊', '猴', '雞', '狗', '豬']
        results = []

        for i in range(12):
            results.append({
                "zodiac": zodiacs[i],
                "zone1": zone1_combos[i]['combo'], # 第一區 6 顆號碼陣列
                "zone2": zone2_ordered[i],         # 第二區 1 顆號碼
                "strategy_type": zone1_combos[i]['type'] # 保留你原本的策略標籤
            })

        return {"status": "success", "data": results}

    except Exception as e:
        return {"status": "error", "message": str(e)}
