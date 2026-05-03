import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(
    api_key=os.getenv("CLAUDE_API_KEY"),
)

SYSTEM_PROMPT = """너는 "공시 요약 인턴"이다.
절대 매수/매도 추천을 하지 않는다.
종목 추천 AI가 아니라, 공시 내용을 정리해주는 인턴이다.

아래 형식으로 답변해라:

📋 공시 요약
- 회사명:
- 공시 유형:
- 핵심 내용: (2~3줄)

⚠️ 리스크 체크
아래 항목을 하나씩 확인하고, 해당 여부를 표시해라.
숫자나 정보가 부족하면 반드시 "원문 확인 필요"라고 써라.

1. 상대방 비공개 여부
2. 계약기간이 너무 긴지 (3년 이상이면 주의)
3. 정정공시 반복 여부 ([정정], [기재정정] 포함 시)
4. 계약금액이 최근 매출 대비 과도한지
5. 최근 주가 급등 여부 (판단 불가 시 "원문 확인 필요")
6. 적자기업의 초대형 계약 여부 (판단 불가 시 "원문 확인 필요")

🔗 원문 링크: (제공된 링크 포함)

⚖️ 이 요약은 투자 판단이 아닌 공시 정리 목적입니다. 반드시 원문을 확인하세요."""


def summarize_disclosure(corp_name, report_nm, rcept_no, rcept_dt):
    """공시 정보를 Claude에게 보내서 요약받기"""

    dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

    user_message = f"""아래 DART 공시를 요약해줘.

회사명: {corp_name}
공시제목: {report_nm}
접수번호: {rcept_no}
접수일: {rcept_dt}
원문링크: {dart_url}

참고:
- 공시 제목만으로 판단 가능한 것만 작성해.
- 모르는 건 "원문 확인 필요"라고 써.
- 절대 매수/매도 의견을 내지 마."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ],
    )

    return response.content[0].text


if __name__ == "__main__":
    print("Claude API 공시 요약 테스트")
    print("=" * 50)
    print()

    # 아까 DART에서 가져온 실제 공시로 테스트
    test_cases = [
        {
            "corp_name": "나노씨엠에스",
            "report_nm": "[기재정정]단일판매·공급계약체결",
            "rcept_no": "20260430902093",
            "rcept_dt": "20260430",
        },
        {
            "corp_name": "톱텍",
            "report_nm": "단일판매·공급계약해지",
            "rcept_no": "20260430901867",
            "rcept_dt": "20260430",
        },
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"--- 테스트 {i}: {case['corp_name']} ---")
        print()

        try:
            summary = summarize_disclosure(
                case["corp_name"],
                case["report_nm"],
                case["rcept_no"],
                case["rcept_dt"],
            )
            print(summary)
        except Exception as e:
            print(f"에러 발생: {e}")

        print()
        print("=" * 50)
        print()