import os
import requests
from dotenv import load_dotenv

# .env 파일에서 API Key 읽어오기
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 보낼 메시지
message = """✅ DART 공시 알림봇 연결 테스트 성공!

이 메시지가 보이면 Telegram 설정이 정상입니다.
앞으로 이 채팅방에 공시 알림이 옵니다."""

# Telegram API로 메시지 보내기
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

response = requests.post(url, json={
    "chat_id": CHAT_ID,
    "text": message,
})

# 결과 확인
if response.status_code == 200:
    print("✅ 텔레그램 메시지 전송 성공!")
else:
    print("❌ 전송 실패!")
    print(f"상태 코드: {response.status_code}")
    print(f"에러 내용: {response.text}")
