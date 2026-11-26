# run_once.py  (프로젝트 루트, main.py와 같은 위치)
# GitHub Actions에서 하루에 한 번 실행하는 진입점.
# main.py처럼 계속 켜져 있지 않고, 날씨 수집 -> 추천 -> 텔레그램 발송을 한 번 하고 끝낸다.
# 중간에 에러가 나면 그대로 실패(빨간 X)로 표시되어 Actions 화면에서 바로 알 수 있다.
from main import get_ai_outfit_rec, get_weather_and_dust, send_telegram_alert


def run():
    weather_data = get_weather_and_dust()
    print(f"날씨 데이터 수집 완료: {weather_data}")

    message = get_ai_outfit_rec(weather_data)
    print(f"추천 완료: {message}")

    send_telegram_alert(message)
    print("텔레그램 발송 완료")


if __name__ == "__main__":
    run()