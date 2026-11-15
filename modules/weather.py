# modules/weather.py
import os
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("DATA_GO_KR_KEY")

# 수원 격자 좌표 (기상청 격자)
NX, NY = 60, 121
# 에어코리아 측정소 이름 (가까운 곳으로 바꾸기)
STATION = "인계동"

PTY = {"0": "없음", "1": "비", "2": "비/눈", "3": "눈",
       "5": "빗방울", "6": "빗방울/눈날림", "7": "눈날림"}


def _get_weather():
    """기상청 초단기실황"""
    now = datetime.now()
    if now.minute < 40:          # 정시 데이터는 매시 40분 이후 제공
        now -= timedelta(hours=1)

    res = requests.get(
        "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst",
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

    return {
        "temp": float(v["T1H"]),
        "humidity": float(v["REH"]),
        "wind": float(v["WSD"]),
        "rain_mm": v["RN1"],
        "condition": PTY.get(v["PTY"], "알 수 없음"),
        "rain": v["PTY"] != "0",
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

    def to_num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    return {"pm10": to_num(item["pm10Value"]),
            "pm25": to_num(item["pm25Value"])}


def get_weather_and_dust():
    data = _get_weather()
    data.update(_get_dust())
    return data


if __name__ == "__main__":
    print(get_weather_and_dust())