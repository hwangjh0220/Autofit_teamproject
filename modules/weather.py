# modules/weather.py
import os
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("DATA_GO_KR_KEY")

# 천안시 동남구 병천면 (기상청 격자)
NX, NY = 66, 109
# 에어코리아 측정소 이름
STATION = "성황동"

FCST = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"

# 강수 형태 (초단기실황 PTY)
PTY = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈",
       "5": "빗방울", "6": "빗방울/눈날림", "7": "눈날림"}
# 하늘 상태 (초단기예보 SKY)
SKY = {"1": "맑음", "3": "구름많음", "4": "흐림"}


def _get_sky():
    """초단기예보에서 가장 가까운 시각의 하늘 상태"""
    now = datetime.now()
    if now.minute < 45:          # 예보는 매시 30분 발표, 45분 이후 제공
        now -= timedelta(hours=1)

    res = requests.get(
        f"{FCST}/getUltraSrtFcst",
        params={
            "serviceKey": KEY, "dataType": "JSON",
            "numOfRows": 60, "pageNo": 1,
            "base_date": now.strftime("%Y%m%d"),
            "base_time": now.strftime("%H30"),
            "nx": NX, "ny": NY,
        }, timeout=10)
    res.raise_for_status()
    items = res.json()["response"]["body"]["items"]["item"]
    sky = sorted((i for i in items if i["category"] == "SKY"),
                 key=lambda i: i["fcstTime"])
    return SKY.get(sky[0]["fcstValue"], "알 수 없음")


def _get_weather():
    """초단기실황 (현재 기온, 습도, 풍속, 강수) + 하늘 상태"""
    now = datetime.now()
    if now.minute < 40:          # 정시 데이터는 매시 40분 이후 제공
        now -= timedelta(hours=1)

    res = requests.get(
        f"{FCST}/getUltraSrtNcst",
        params={
            "serviceKey": KEY, "dataType": "JSON",
            "numOfRows": 20, "pageNo": 1,
            "base_date": now.strftime("%Y%m%d"),
            "base_time": now.strftime("%H00"),
            "nx": NX, "ny": NY,
        }, timeout=10)
    res.raise_for_status()
    items = res.json()["response"]["body"]["items"]["item"]
    v = {i["category"]: i["obsrValue"] for i in items}

    raining = v["PTY"] != "0"
    condition = PTY.get(v["PTY"], "알 수 없음") if raining else _get_sky()

    return {
        "temp": float(v["T1H"]),          # 현재 기온(°C)
        "humidity": float(v["REH"]),      # 습도(%)
        "wind": float(v["WSD"]),          # 풍속(m/s)
        "rain_mm": v["RN1"],              # 1시간 강수량
        "condition": condition,
        "rain": raining,
    }


def _fetch_vilage(base_date, base_time):
    """단기예보 원본 항목 리스트"""
    res = requests.get(
        f"{FCST}/getVilageFcst",
        params={
            "serviceKey": KEY, "dataType": "JSON",
            "numOfRows": 1000, "pageNo": 1,
            "base_date": base_date, "base_time": base_time,
            "nx": NX, "ny": NY,
        }, timeout=10)
    res.raise_for_status()
    return res.json()["response"]["body"]["items"]["item"]


def _get_forecast():
    """단기예보: 오늘 최저/최고기온(TMN, TMX)과 강수확률(POP)"""
    now = datetime.now()
    today = now.strftime("%Y%m%d")

    # 1) 최저/최고기온은 02시 발표분에 들어 있음 (02:10 이후 제공)
    day = now if (now.hour, now.minute) >= (2, 10) else now - timedelta(days=1)
    items = _fetch_vilage(day.strftime("%Y%m%d"), "0200")
    tmn = [float(i["fcstValue"]) for i in items
           if i["category"] == "TMN" and i["fcstDate"] == today]
    tmx = [float(i["fcstValue"]) for i in items
           if i["category"] == "TMX" and i["fcstDate"] == today]

    # 2) 강수확률은 가장 최근 발표분에서 지금 이후 가장 가까운 시각의 값
    t = now - timedelta(minutes=10)      # 발표 후 약 10분 뒤부터 제공
    hours = [h for h in (2, 5, 8, 11, 14, 17, 20, 23) if h <= t.hour]
    if hours:
        pop_date, pop_time = t.strftime("%Y%m%d"), f"{hours[-1]:02d}00"
    else:                                 # 02시 이전이면 전날 23시 발표분
        pop_date = (t - timedelta(days=1)).strftime("%Y%m%d")
        pop_time = "2300"
    items = _fetch_vilage(pop_date, pop_time)

    now_key = now.strftime("%Y%m%d%H00")
    pops = sorted((i["fcstDate"] + i["fcstTime"], int(i["fcstValue"]))
                  for i in items if i["category"] == "POP")
    future = [p for k, p in pops if k >= now_key]
    pop = future[0] if future else (pops[-1][1] if pops else 0)

    return {
        "min_temp": tmn[0] if tmn else None,
        "max_temp": tmx[0] if tmx else None,
        "pop": pop,                       # 강수확률(%)
    }


def _get_dust():
    """에어코리아 측정소별 실시간 측정정보"""
    res = requests.get(
        "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty",
        params={
            "serviceKey": KEY, "returnType": "json",
            "numOfRows": 1, "pageNo": 1,
            "stationName": STATION, "dataTerm": "DAILY", "ver": "1.3",
        }, timeout=10)
    res.raise_for_status()
    item = res.json()["response"]["body"]["items"][0]

    def to_num(x):                      # 점검 중이면 "-"가 옴
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    return {"pm10": to_num(item["pm10Value"]),
            "pm25": to_num(item["pm25Value"])}


def get_weather_and_dust():
    data = _get_weather()
    data.update(_get_forecast())
    data.update(_get_dust())

    # 추천 모듈이 숫자를 기대하므로, 비어 있으면 현재 기온으로 대체
    if data["min_temp"] is None:
        data["min_temp"] = data["temp"]
    if data["max_temp"] is None:
        data["max_temp"] = data["temp"]
    return data


if __name__ == "__main__":
    print(get_weather_and_dust())