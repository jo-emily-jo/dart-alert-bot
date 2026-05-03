import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from db_setup import init_db, is_seen, save_disclosure, get_past_disclosures

load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY")

KEYWORDS = [
    "단일판매",
    "공급계약",
    "수주",
    "시설투자",
    "신규시설투자",
    "유형자산취득",
    "타법인 주식 및 출자증권 취득",
]

init_db()

today = datetime.now()
week_ago = today - timedelta(days=7)

url = "https://opendart.fss.or.kr/api/list.json"
params = {
    "crtfc_key": DART_API_KEY,
    "bgn_de": week_ago.strftime("%Y%m%d"),
    "end_de": today.strftime("%Y%m%d"),
    "page_count": 100,
}

print(f"DART 공시 조회 중... ({week_ago.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')})")
print()

response = requests.get(url, params=params)

if response.status_code != 200:
    print(f"API 호출 실패! 상태 코드: {response.status_code}")
    exit()

data = response.json()
status = data.get("status")

if status == "000":
    total = data.get("total_count", 0)
    print(f"전체 공시 {total}건 중 {len(data['list'])}건 가져옴")
elif status == "013":
    print("조회된 공시가 0건입니다.")
    exit()
else:
    print(f"DART API 에러: {data.get('message')}")
    exit()

new_matched = []
already_seen = 0

for item in data["list"]:
    title = item.get("report_nm", "")
    rcept_no = item.get("rcept_no", "")

    for keyword in KEYWORDS:
        if keyword in title:
            if is_seen(rcept_no):
                already_seen += 1
            else:
                save_disclosure(item, matched_keyword=keyword)
                new_matched.append(item)
            break

print(f"키워드 매칭: {len(new_matched) + already_seen}건")
print(f"  - 새로운 공시: {len(new_matched)}건")
print(f"  - 이미 본 공시: {already_seen}건 (중복 알림 방지됨)")
print()

if new_matched:
    for i, item in enumerate(new_matched[:10], 1):
        corp = item.get("corp_name", "?")
        print(f"--- {i}번째 새 공시 ---")
        print(f"  회사명:   {corp}")
        print(f"  공시제목: {item.get('report_nm', '?')}")
        print(f"  접수번호: {item.get('rcept_no', '?')}")
        print(f"  접수일:   {item.get('rcept_dt', '?')}")

        past = get_past_disclosures(corp)
        if len(past) > 1:
            print(f"  >> 이 회사 과거 공시 {len(past)}건 발견! (반복 수주 가능성)")
        print()
else:
    print("이번에는 새로운 매칭 공시가 없습니다.")
    print()
    print("참고로 가져온 공시 제목 5개:")
    for item in data["list"][:5]:
        print(f"  - [{item.get('corp_name')}] {item.get('report_nm')}")

print()
print("다시 실행하면 같은 공시는 이미 본 공시로 처리됩니다.")