"""2번 모듈: 옷장 데이터 + 날씨 기반 옷차림 추천 (Gemini 사용, 실패 시 규칙 기반 대체)

weather.py 가 넘겨줄 날씨 dict 형식 (팀원과 합의한 약속):
    {
        "min_temp": 8.0,   # 최저기온(℃)  - 기상청 TMN
        "max_temp": 19.0,  # 최고기온(℃)  - 기상청 TMX
        "pop": 30,         # 강수확률(%)  - 기상청 POP
        "wind": 2.5,       # 풍속(m/s)    - 기상청 WSD
        "pm10": 45,        # 미세먼지(㎍/㎥) - 에어코리아 pm10Value
        "pm25": 20,        # 초미세먼지(㎍/㎥) - 에어코리아 pm25Value
    }
"""
import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()  # .env 파일의 키를 환경변수로 불러옴 (키는 코드에 직접 쓰지 않는다)
except ImportError:
    pass

WARDROBE_PATH = Path(__file__).resolve().parent.parent / "data" / "wardrobe.json"


# ---------- 1) 날씨 계산 ----------
def feels_like(temp: float, wind_ms: float) -> float:
    """체감온도(기상청 겨울철 공식). 10℃ 이하 + 풍속 1.3m/s 이상일 때만 바람 영향 반영."""
    v = wind_ms * 3.6  # m/s -> km/h
    if temp > 10 or v < 4.8:
        return temp
    return 13.12 + 0.6215 * temp - 11.37 * v ** 0.16 + 0.3965 * v ** 0.16 * temp


def pm_grade(pm10: float, pm25: float) -> str:
    """미세먼지 등급 (에어코리아 기준). 둘 중 나쁜 쪽을 따른다."""
    def g10(v): return 0 if v <= 30 else 1 if v <= 80 else 2 if v <= 150 else 3
    def g25(v): return 0 if v <= 15 else 1 if v <= 35 else 2 if v <= 75 else 3
    return ["좋음", "보통", "나쁨", "매우나쁨"][max(g10(pm10), g25(pm25))]


# ---------- 2) 옷장 필터링 ----------
def load_wardrobe(path=WARDROBE_PATH) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def pick_clothes(temp: float, wardrobe: list[dict]) -> dict[str, list[str]]:
    """해당 기온에 맞는 옷을 카테고리별로 추려서 반환."""
    result: dict[str, list[str]] = {}
    for item in wardrobe:
        if item["min_temp"] <= temp <= item["max_temp"]:
            result.setdefault(item["category"], []).append(item["name"])
    return result


# ---------- 3) 규칙 기반 추천 (AI 실패 시에도 항상 동작) ----------
def rule_based_advice(w: dict, wardrobe: list[dict] | None = None) -> str:
    wardrobe = load_wardrobe() if wardrobe is None else wardrobe
    t_min = feels_like(w["min_temp"], w.get("wind", 0))
    t_max = feels_like(w["max_temp"], w.get("wind", 0))
    ref = (t_min + t_max) / 2
    grade = pm_grade(w.get("pm10", 0), w.get("pm25", 0))

    lines = [f"🌡 최저 {w['min_temp']:.0f}℃ / 최고 {w['max_temp']:.0f}℃ (체감 {ref:.0f}℃)"]

    clothes = pick_clothes(ref, wardrobe)
    if clothes:
        outfit = " · ".join(f"{cat}: {', '.join(names[:2])}" for cat, names in clothes.items())
        lines.append(f"👕 {outfit}")
    if w["max_temp"] - w["min_temp"] >= 10:
        lines.append("🧥 일교차가 커요. 벗고 입기 편한 겉옷을 챙기세요.")

    pop = w.get("pop", 0)
    if pop >= 60:
        lines.append(f"☔ 강수확률 {pop}%! 우산 필수")
    elif pop >= 30:
        lines.append(f"🌂 강수확률 {pop}%, 접이식 우산 챙기세요")

    if grade in ("나쁨", "매우나쁨"):
        lines.append(f"😷 미세먼지 {grade} — KF 마스크 착용")
    else:
        lines.append(f"🍃 미세먼지 {grade}")
    return "\n".join(lines)


# ---------- 4) Gemini 추천 ----------
def generate_outfit_advice(w: dict, wardrobe: list[dict] | None = None) -> str:
    """main.py 에서 호출하는 핵심 함수. 항상 문자열을 반환한다."""
    base = rule_based_advice(w, wardrobe)          # AI가 근거로 삼을 기본 추천
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return base                                 # 키가 없으면 규칙 기반으로 대체

    prompt = f"""너는 친근한 아침 코디 도우미야.
아래 '기본 추천'을 바탕으로, 텔레그램 메시지용으로 5줄 이내로 자연스럽게 다듬어줘.
옷은 반드시 '기본 추천'에 있는 옷장 아이템 위주로 말하고, 없는 옷을 지어내지 마.
이모지를 적당히 쓰고, 마지막에 한 줄 응원 멘트를 넣어줘.

[날씨]
최저 {w['min_temp']}℃, 최고 {w['max_temp']}℃, 강수확률 {w.get('pop', 0)}%,
풍속 {w.get('wind', 0)}m/s, 미세먼지 {w.get('pm10')}(초미세 {w.get('pm25')})

[기본 추천]
{base}
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        res = client.models.generate_content(model=model, contents=prompt)
        text = (res.text or "").strip()
        return text or base
    except Exception as e:  # 네트워크/쿼터/키 오류 등 -> 아침 알림이 끊기지 않게 대체
        print(f"[recommendation] Gemini 호출 실패, 규칙 기반으로 대체: {e}")
        return base


if __name__ == "__main__":
    sample = {"min_temp": 8, "max_temp": 19, "pop": 40, "wind": 3.0, "pm10": 85, "pm25": 30}
    print(generate_outfit_advice(sample))

    # ---------- 5) main.py 연동용 (main.py가 부르는 이름) ----------
def _num(d: dict, keys: list, default=None):
    """여러 후보 키 중 처음 발견되는 숫자 값을 반환. 못 찾으면 default."""
    for k in keys:
        v = d.get(k)
        if v in (None, "", "-"):
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return default


def normalize_weather(raw: dict) -> dict:
    """weather.py 가 주는 dict(키 이름이 달라도)를 이 모듈이 쓰는 형식으로 변환."""
    cur = _num(raw, ["temp", "TMP", "tmp", "temperature"])
    t_min = _num(raw, ["min_temp", "TMN", "tmn", "temp_min", "tmin"], cur)
    t_max = _num(raw, ["max_temp", "TMX", "tmx", "temp_max", "tmax"], cur)
    if t_min is None and t_max is None:
        raise ValueError(f"기온 값을 찾을 수 없습니다. 받은 키: {list(raw.keys())}")
    t_min = t_max if t_min is None else t_min
    t_max = t_min if t_max is None else t_max
    if t_min > t_max:
        t_min, t_max = t_max, t_min
    return {
        "min_temp": t_min,
        "max_temp": t_max,
        "pop": _num(raw, ["pop", "POP", "rain_prob"], 0),
        "wind": _num(raw, ["wind", "WSD", "wsd", "wind_speed"], 0),
        "pm10": _num(raw, ["pm10", "pm10Value", "pm10_value"], 0),
        "pm25": _num(raw, ["pm25", "pm25Value", "pm25_value"], 0),
    }


def get_ai_outfit_rec(weather_data: dict) -> str:
    """main.py 에서 호출: 날씨 dict -> 추천 문장(str)"""
    return generate_outfit_advice(normalize_weather(weather_data))
