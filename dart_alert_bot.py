import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import anthropic
from db_setup import init_db, is_seen, save_disclosure, get_past_disclosures

load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

KEYWORDS = [
    "단일판매",
    "공급계약",
    "수주",
    "시설투자",
    "신규시설투자",
    "유형자산취득",
    "타법인 주식 및 출자증권 취득",
]

SYSTEM_PROMPT = """너는 "공시 요약 인턴"이다.
절대 매수/매도 추천을 하지 않는다.
종목 추천 AI가 아니라, 공시 내용을 정리해주는 인턴이다.

아래 형식으로 답변해라:

공시 요약
- 회사명:
- 공시 유형:
- 핵심 내용: (2~3줄)

리스크 체크
아래 항목을 하나씩 확인하고, 해당 여부를 표시해라.
숫자나 정보가 부족하면 반드시 "원문 확인 필요"라고 써라.

1. 상대방 비공개 여부
2. 계약기간이 너무 긴지 (3년 이상이면 주의)
3. 정정공시 반복 여부
4. 계약금액이 최근 매출 대비 과도한지
5. 최근 주가 급등 여부 (판단 불가 시 "원문 확인 필요")
6. 적자기업의 초대형 계약 여부 (판단 불가 시 "원문 확인 필요")

이 요약은 투자 판단이 아닌 공시 정리 목적입니다. 반드시 원문을 확인하세요."""


def fetch_dart_disclosures():
    """DART에서 최근 공시 가져오기"""
    today = datetime.now()
    week_ago = today - timedelta(days=7)

    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": DART_API_KEY,
        "bgn_de": week_ago.strftime("%Y%m%d"),
        "end_de": today.strftime("%Y%m%d"),
        "page_count": 100,
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"DART API 호출 실패: {response.status_code}")
        return []

    data = response.json()
    if data.get("status") != "000":
        print(f"DART API 에러: {data.get('message', '공시 없음')}")
        return []

    return data.get("list", [])


def filter_new_disclosures(items):
    """키워드 매칭 + 중복 제거"""
    new_items = []
    for item in items:
        title = item.get("report_nm", "")
        rcept_no = item.get("rcept_no", "")

        for keyword in KEYWORDS:
            if keyword in title:
                if not is_seen(rcept_no):
                    save_disclosure(item, matched_keyword=keyword)
                    new_items.append(item)
                break

    return new_items


def summarize_with_claude(corp_name, report_nm, rcept_no, rcept_dt, past_history=""):
    """Claude API로 공시 요약"""
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

    user_message = f"""아래 DART 공시를 요약해줘.

회사명: {corp_name}
공시제목: {report_nm}
접수번호: {rcept_no}
접수일: {rcept_dt}
원문링크: {dart_url}
"""

    if past_history:
        user_message += f"""
이 회사의 과거 공시 이력:
{past_history}
과거 공시와 비교하여 반복 수주 여부도 언급해줘.
"""

    user_message += """
참고:
- 공시 제목만으로 판단 가능한 것만 작성해.
- 모르는 건 "원문 확인 필요"라고 써.
- 절대 매수/매도 의견을 내지 마."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except Exception as e:
        return f"Claude 요약 실패: {e}"


def send_telegram(message):
    """Telegram으로 메시지 보내기"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    # Telegram 메시지 길이 제한 (4096자)
    if len(message) > 4000:
        message = message[:4000] + "\n\n... (메시지가 잘렸습니다. 원문을 확인하세요)"

    response = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": message,
    })

    if response.status_code != 200:
        print(f"Telegram 전송 실패: {response.text}")
        return False
    return True


def build_past_history(corp_name):
    """과거 공시 이력을 텍스트로 만들기"""
    past = get_past_disclosures(corp_name)
    if not past:
        return ""

    lines = []
    for row in past:
        rcept_dt, report_nm, contract_amount, counterparty = row
        line = f"- {rcept_dt}: {report_nm}"
        if contract_amount:
            line += f" (계약금액: {contract_amount:,}원)"
        if counterparty:
            line += f" (상대방: {counterparty})"
        lines.append(line)

    return "\n".join(lines)


def main():
    print(f"=== DART 공시 알림봇 실행 ({datetime.now().strftime('%Y-%m-%d %H:%M')}) ===")
    print()

    # 1. DB 초기화
    init_db()

    # 2. DART 공시 가져오기
    items = fetch_dart_disclosures()
    if not items:
        print("가져온 공시가 없습니다.")
        return

    print(f"전체 공시 {len(items)}건 가져옴")

    # 3. 키워드 필터링 + 중복 제거
    new_items = filter_new_disclosures(items)
    print(f"새로운 매칭 공시: {len(new_items)}건")
    print()

    if not new_items:
        print("새로운 알림 대상 공시가 없습니다.")
        return

    # 4. 각 공시에 대해 Claude 요약 + Telegram 전송
    for i, item in enumerate(new_items, 1):
        corp_name = item.get("corp_name", "?")
        report_nm = item.get("report_nm", "?")
        rcept_no = item.get("rcept_no", "?")
        rcept_dt = item.get("rcept_dt", "?")
        dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

        print(f"--- {i}/{len(new_items)}: {corp_name} ---")

        # 과거 이력 조회
        past_history = build_past_history(corp_name)

        # Claude 요약
        print("  Claude 요약 중...")
        summary = summarize_with_claude(
            corp_name, report_nm, rcept_no, rcept_dt, past_history
        )

        # Telegram 메시지 구성
        telegram_msg = f"""[DART 공시 알림]

{summary}

원문 링크: {dart_url}"""

        # Telegram 전송
        if send_telegram(telegram_msg):
            print("  Telegram 전송 완료!")
        else:
            print("  Telegram 전송 실패!")

        print()

    print(f"=== 완료: {len(new_items)}건 알림 전송 ===")


if __name__ == "__main__":
    main()