# main.py

import time
import schedule
from dotenv import load_dotenv

# 아직 파일이 없거나 완성되지 않았다면 임시 주석 처리
from modules.weather import get_weather_and_dust       
# from modules.recommendation import get_ai_outfit_rec  
# from modules.notifier import send_telegram_alert      

load_dotenv()

def job_pipeline():
    print("[WearCast] 아침 루틴 파이프라인 실행 중...")
    
    try:
        # 1. 기상청/미세먼지 (팀원 1이 구현 중)
        weather_data = get_weather_and_dust()
        # weather_data = {"temp": 15.0, "condition": "맑음", "pm10": 30} # 임시 테스트용 더미 데이터
        print(f"날씨 데이터 수집 완료: {weather_data}")

        # 2. 옷장 & AI 추천 (팀원 2가 구현 중)
        # ai_recommendation = get_ai_outfit_rec(weather_data)
        ai_recommendation = "오늘은 맑고 온화하니 셔츠와 슬랙스를 추천합니다!" # 임시 테스트용
        print(f"AI 추천 완료: {ai_recommendation}")

        # 3. 텔레그램 발송 (팀원 3이 구현 중)
        # send_telegram_alert(ai_recommendation)
        print("텔레그램 발송 완료 (현재는 테스트 모드)")

    except Exception as e:
        print(f"에러 발생: {e}")

def main():
    print(" WearCast 서비스가 시작되었습니다. (스케줄러 대기 중...)")
    
    # 테스트할 때는 10초마다 돌려볼 수도 있습니다 (schedule.every(10).seconds)
    schedule.every().day.at("07:30").do(job_pipeline)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()