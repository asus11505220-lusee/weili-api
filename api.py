from fastapi import FastAPI, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware

# 載入你剛剛寫好接孔的兩支神級引擎
import weili_v8_engine
import gichier539_engine

app = FastAPI(title="生肖威力今彩 API (加密防護版)")

# 🔒 你的防小人金鑰 (可以自己亂敲改成更複雜的)
API_KEY = "Fortune2026-SuperKey"
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

# 開放 Thunkable 跨域連線
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 門禁檢查邏輯
async def check_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return api_key
    raise HTTPException(status_code=403, detail="🔒 密鑰錯誤或未授權，拒絕惡意連線！")

# 🔵 威力彩專屬網址
@app.get("/generate")
def generate_weili(zodiac_id: int = 1, api_key: str = Security(check_api_key)):
    return weili_v8_engine.get_prediction(zodiac_id)

# 🟢 今彩539專屬網址
@app.get("/generate_539")
def generate_539(zodiac_id: int = 1, api_key: str = Security(check_api_key)):
    return gichier539_engine.get_prediction(zodiac_id)
