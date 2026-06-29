"""
Korexis 리드 레이더 (lead mode)
================================
"호주 진출 + AASB S2 기후공시 노출 가능성 있는 한국 기업"을 DART 공시에서
탐지·랭킹한다. 투자 리스크 평가가 아니라 Korexis 영업 fit 평가다.

기존 투자 알림봇(dart_alert_bot.py)과 **완전히 분리된 별도 진입점**이다.
공유 인프라(DART/Claude/Telegram 호출 방식, 같은 SQLite 파일)는 재사용하되
투자봇의 코드 경로(키워드7종 → 리스크6 → 텔레그램)는 건드리지 않는다.

실행:  python lead_radar.py
출력:  candidates.csv  (fit_score 내림차순) + (선택) 텔레그램 알림

탐지·랭킹까지만 한다. 자동 아웃리치/메일 발송 기능은 의도적으로 없다.
공개 법인 공시 데이터만 다루며 개인 신상은 수집하지 않는다.
"""

import os
import re
import io
import csv
import json
import time
import zipfile
import sqlite3
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
import anthropic

# 투자봇과 동일한 텔레그램 전송을 그대로 재사용 (해당 모듈은 수정하지 않음).
# import 시점에 dart_alert_bot.main()은 __main__ 가드로 실행되지 않는다.
from dart_alert_bot import send_telegram

load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY")
# 투자봇과 키 이름 통일: ANTHROPIC_API_KEY가 아니라 CLAUDE_API_KEY 사용.
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

DB_PATH = "seen_disclosures.db"           # 투자봇과 같은 파일, 별도 테이블 사용
CSV_PATH = "candidates.csv"

# ── 동작 파라미터 ────────────────────────────────────────────────
LOOKBACK_DAYS = 30                         # 최근 30일
PBLNTF_TYPES = ["A", "B"]                  # A=정기공시, B=주요사항보고서
PAGE_COUNT = 100                           # list.json 페이지당 최대 100
MAX_PAGES_PER_TYPE = 20                    # 공시유형별 최대 페이지 (안전장치)
MAX_DOCS_TO_SCAN = 300                     # 본문 스캔 상한 (rate limit 보호)
DOC_FETCH_SLEEP = 0.4                      # document.xml 호출 간 간격(초)
SEND_TELEGRAM = True                       # CSV + 텔레그램
TELEGRAM_FIT_THRESHOLD = 60               # 이 점수 이상만 텔레그램 알림
CLAUDE_MODEL = "claude-sonnet-4-6"

# ── 키워드 사전 ─────────────────────────────────────────────────
# 1차(필수): 하나도 없으면 후보에서 탈락 (gate)
PRIMARY_KEYWORDS = ["호주", "오세아니아", "Australia", "AUSTRALIA"]

# 2차(가중): 매칭될 때마다 점수 가산. AASB S2(기후공시) 연관 키워드에 높은 가중치.
SECONDARY_WEIGHTS = {
    # 기후/ESG (AASB S2 노출 신호 — 가장 중요)
    "기후": 3, "탄소": 3, "온실가스": 3, "ESG": 3, "지속가능": 3,
    # 현지 진출/법인 신호
    "현지법인": 2, "자회사": 2, "진출": 2, "설립": 2,
    # 사업/거래 신호
    "계약": 1, "매출": 1, "수출": 1, "글로벌": 1,
}

# NOT 감점(선택): Korexis fit이 낮은 업종 신호
NEGATIVE_WEIGHTS = {"건설": 3, "조선": 3, "방산": 3}

PRIMARY_BASE_SCORE = 5                      # 1차 키워드 존재 시 기본 점수

LEAD_SYSTEM_PROMPT = """너는 Korexis의 B2B 영업 리서치 애널리스트다.
Korexis는 한국 기업의 **호주(오세아니아) 시장 진출**과 호주 회계기준
**AASB S2 기후 관련 재무공시** 대응을 돕는 컨설팅 회사다.

너의 임무는 주어진 DART 공시 본문을 읽고, 이 회사가 Korexis의 잠재 고객
(영업 리드)으로서 얼마나 적합한지 평가하는 것이다.
**투자 매수/매도 의견이나 투자 리스크 평가는 절대 하지 마라.** 영업 fit만 본다.

평가 기준:
- 호주/오세아니아 진출, 현지법인·자회사 설립, 현지 매출·수출·계약 신호
- 기후·탄소·온실가스·ESG·지속가능 관련 활동(= AASB S2 공시 의무 노출 가능성)
- 업종이 Korexis 서비스와 맞는지

반드시 아래 JSON 형식으로만 답하라. 다른 텍스트는 출력하지 마라.
{
  "fit_score": 0~100 사이 정수,
  "업종": "추정 업종 (간단히)",
  "호주_연관_근거": "본문에서 호주/오세아니아 연관성을 보여주는 구체적 근거. 근거 없으면 '뚜렷한 근거 없음'",
  "추천_접근앵글": "Korexis 영업 담당자가 쓸 만한 접근 각도 한 줄",
  "보류사유": "리드로 부적합하거나 확인이 더 필요하면 그 이유. 없으면 빈 문자열"
}
"""


# ════════════════════════════════════════════════════════════════
# DB: 투자봇 테이블과 분리된 lead_candidates 테이블 (같은 파일)
# ════════════════════════════════════════════════════════════════
def init_lead_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lead_candidates (
        rcept_no         TEXT PRIMARY KEY,
        corp_code        TEXT,
        corp_name        TEXT,
        report_nm        TEXT,
        rcept_dt         TEXT,
        matched_keywords TEXT,
        candidate_score  INTEGER,
        fit_score        INTEGER,
        industry         TEXT,
        australia_basis  TEXT,
        approach_angle   TEXT,
        hold_reason      TEXT,
        dart_url         TEXT,
        scored_at        TEXT DEFAULT (datetime('now', 'localtime'))
    )
    """)
    conn.commit()
    conn.close()


def is_scored(rcept_no):
    """이미 lead로 스코어링한 공시인지 확인 (재스코어링 방지)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM lead_candidates WHERE rcept_no = ?", (rcept_no,))
    found = cur.fetchone() is not None
    conn.close()
    return found


def save_lead(row):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    INSERT OR IGNORE INTO lead_candidates
        (rcept_no, corp_code, corp_name, report_nm, rcept_dt,
         matched_keywords, candidate_score, fit_score, industry,
         australia_basis, approach_angle, hold_reason, dart_url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        row["rcept_no"], row["corp_code"], row["corp_name"], row["report_nm"],
        row["rcept_dt"], row["matched_keywords"], row["candidate_score"],
        row["fit_score"], row["industry"], row["australia_basis"],
        row["approach_angle"], row["hold_reason"], row["dart_url"],
    ))
    conn.commit()
    conn.close()


# ════════════════════════════════════════════════════════════════
# DART fetch (페이지네이션 + 백오프) — 투자봇 fetch를 lead 용으로 일반화
# ════════════════════════════════════════════════════════════════
def _dart_get(url, params, max_retries=3):
    """공통 GET + 지수 백오프. 응답 객체 반환(실패 시 None)."""
    delay = 1.0
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                return resp
            print(f"  HTTP {resp.status_code} (재시도 {attempt+1}/{max_retries})")
        except requests.RequestException as e:
            print(f"  요청 예외: {e} (재시도 {attempt+1}/{max_retries})")
        time.sleep(delay)
        delay *= 2
    return None


def fetch_lead_disclosures():
    """list.json에서 pblntf_ty=A,B + 최근 30일 공시를 페이지네이션으로 수집."""
    today = datetime.now()
    start = today - timedelta(days=LOOKBACK_DAYS)
    url = "https://opendart.fss.or.kr/api/list.json"

    collected = {}  # rcept_no -> item (유형 간 중복 제거)
    for ty in PBLNTF_TYPES:
        page = 1
        while page <= MAX_PAGES_PER_TYPE:
            params = {
                "crtfc_key": DART_API_KEY,
                "bgn_de": start.strftime("%Y%m%d"),
                "end_de": today.strftime("%Y%m%d"),
                "pblntf_ty": ty,
                "page_no": page,
                "page_count": PAGE_COUNT,
            }
            resp = _dart_get(url, params)
            if resp is None:
                print(f"  [{ty}] page {page} 조회 실패 — 이 유형 중단")
                break

            data = resp.json()
            status = data.get("status")
            if status == "013":  # 조회된 데이터 없음
                break
            if status != "000":
                print(f"  [{ty}] DART status={status}: {data.get('message')}")
                break

            for item in data.get("list", []):
                collected[item.get("rcept_no", "")] = item

            total_page = int(data.get("total_page", 1))
            if page >= total_page:
                break
            page += 1
            time.sleep(0.2)

        if page > MAX_PAGES_PER_TYPE:
            print(f"  [{ty}] MAX_PAGES_PER_TYPE={MAX_PAGES_PER_TYPE} 도달 — 일부 공시는 스캔에서 제외됨")

    return list(collected.values())


def get_document_text_full(rcept_no, max_chars=None):
    """document.xml 원문 전체 텍스트.

    투자봇 get_document_text()의 일반화 버전. 키워드 스캔을 위해 기본은
    잘림 없이(max_chars=None) 전체를 반환한다. (V2 raw_text 로드맵에서도
    재사용 가능하도록 분리)
    """
    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {"crtfc_key": DART_API_KEY, "rcept_no": rcept_no}
    resp = _dart_get(url, params)
    if resp is None:
        return None
    try:
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        names = z.namelist()
        if not names:
            return None
        xml = z.read(names[0]).decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", xml)
        text = re.sub(r"\.xforms[^}]+\}", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if max_chars and len(text) > max_chars:
            text = text[:max_chars] + " (이하 생략)"
        return text
    except Exception as e:
        print(f"  원문 파싱 실패({rcept_no}): {e}")
        return None


# ════════════════════════════════════════════════════════════════
# 로컬 키워드 스코어링
# ════════════════════════════════════════════════════════════════
def score_candidate(text):
    """본문 텍스트 → (candidate_score, matched_keywords list).

    1차 키워드가 하나도 없으면 candidate_score=None (탈락 신호).
    """
    primary_hits = [k for k in PRIMARY_KEYWORDS if k in text]
    if not primary_hits:
        return None, []

    matched = list(dict.fromkeys(primary_hits))  # 표시용(중복 제거, 순서 유지)
    score = PRIMARY_BASE_SCORE

    for kw, w in SECONDARY_WEIGHTS.items():
        if kw in text:
            score += w
            matched.append(kw)
    for kw, w in NEGATIVE_WEIGHTS.items():
        if kw in text:
            score -= w
            matched.append(f"-{kw}")

    return score, matched


# ════════════════════════════════════════════════════════════════
# Claude fit 스코어링 (신규 프롬프트, JSON 출력)
# ════════════════════════════════════════════════════════════════
def claude_fit_score(corp_name, report_nm, raw_text):
    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

    # 토큰 보호: 본문은 앞 8000자까지만 Claude에 전달 (스캔은 전체로 이미 끝남)
    body = raw_text[:8000] if raw_text else ""
    user_msg = f"""아래 DART 공시를 읽고 Korexis 영업 리드 적합도를 평가해줘.

회사명: {corp_name}
공시제목: {report_nm}

=== 공시 본문 ===
{body}
=== 본문 끝 ===

위 회사가 호주 진출 + AASB S2 기후공시 대응 관점에서 Korexis 고객으로
적합한지 JSON으로만 답해라."""

    fallback = {
        "fit_score": 0, "업종": "", "호주_연관_근거": "",
        "추천_접근앵글": "", "보류사유": "Claude 평가 실패",
    }
    try:
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=800,
            system=LEAD_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = resp.content[0].text.strip()
        # JSON 블록만 추출 (코드펜스나 군더더기 대비)
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            fallback["보류사유"] = "Claude JSON 파싱 실패"
            return fallback
        data = json.loads(m.group(0))
        return {
            "fit_score": int(data.get("fit_score", 0)),
            "업종": str(data.get("업종", "")),
            "호주_연관_근거": str(data.get("호주_연관_근거", "")),
            "추천_접근앵글": str(data.get("추천_접근앵글", "")),
            "보류사유": str(data.get("보류사유", "")),
        }
    except Exception as e:
        fallback["보류사유"] = f"Claude 평가 실패: {e}"
        return fallback


# ════════════════════════════════════════════════════════════════
# 출력
# ════════════════════════════════════════════════════════════════
CSV_HEADER = [
    "기업명", "corp_code", "공시제목", "rcept_no", "접수일",
    "매칭키워드", "candidate_score", "fit_score", "접근앵글", "dart원문링크",
]


def write_csv(rows):
    """fit_score 내림차순으로 candidates.csv 작성."""
    rows_sorted = sorted(rows, key=lambda r: r["fit_score"], reverse=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for r in rows_sorted:
            w.writerow([
                r["corp_name"], r["corp_code"], r["report_nm"], r["rcept_no"],
                r["rcept_dt"], r["matched_keywords"], r["candidate_score"],
                r["fit_score"], r["approach_angle"], r["dart_url"],
            ])
    return rows_sorted


def notify_telegram(rows_sorted):
    """fit_score 높은 리드를 투자봇과 구분되는 포맷으로 알림."""
    leads = [r for r in rows_sorted if r["fit_score"] >= TELEGRAM_FIT_THRESHOLD]
    if not leads:
        print("텔레그램 알림 대상(fit_score>=%d) 없음" % TELEGRAM_FIT_THRESHOLD)
        return
    for r in leads:
        msg = f"""🎯 [Korexis 리드 레이더]

회사: {r['corp_name']} (fit {r['fit_score']}/100)
업종: {r['industry']}
공시: {r['report_nm']} ({r['rcept_dt']})
호주 연관: {r['australia_basis']}
접근앵글: {r['approach_angle']}
매칭: {r['matched_keywords']}

🔗 {r['dart_url']}

* 영업 리드 탐지 결과입니다. 투자 의견이 아닙니다."""
        send_telegram(msg)
    print(f"텔레그램 리드 알림 {len(leads)}건 전송")


# ════════════════════════════════════════════════════════════════
def main():
    print(f"=== Korexis 리드 레이더 실행 ({datetime.now():%Y-%m-%d %H:%M}) ===\n")
    if not DART_API_KEY or not CLAUDE_API_KEY:
        print("환경변수 DART_API_KEY / CLAUDE_API_KEY 가 필요합니다 (.env 확인).")
        return

    init_lead_db()

    print(f"[1/3] DART 공시 수집 (유형 {PBLNTF_TYPES}, 최근 {LOOKBACK_DAYS}일)...")
    items = fetch_lead_disclosures()
    print(f"  수집된 공시: {len(items)}건")

    # 이미 스코어링한 공시 제외 (중복제거)
    fresh = [it for it in items if not is_scored(it.get("rcept_no", ""))]
    print(f"  미스코어링 공시: {len(fresh)}건")

    if len(fresh) > MAX_DOCS_TO_SCAN:
        print(f"  ⚠ 본문 스캔 상한 MAX_DOCS_TO_SCAN={MAX_DOCS_TO_SCAN} 적용 — "
              f"{len(fresh) - MAX_DOCS_TO_SCAN}건은 이번 실행에서 제외(다음 실행에서 처리).")
        fresh = fresh[:MAX_DOCS_TO_SCAN]

    print(f"\n[2/3] 본문 스캔 + 로컬 키워드 스코어링 ({len(fresh)}건)...")
    candidates = []
    for i, it in enumerate(fresh, 1):
        rcept_no = it.get("rcept_no", "")
        corp_name = it.get("corp_name", "?")
        text = get_document_text_full(rcept_no)
        time.sleep(DOC_FETCH_SLEEP)
        if not text:
            continue
        cand_score, matched = score_candidate(text)
        if cand_score is None:
            continue  # 1차 키워드 없음 → 탈락
        candidates.append({"item": it, "text": text,
                           "candidate_score": cand_score, "matched": matched})
        print(f"  [{i}/{len(fresh)}] 후보: {corp_name} "
              f"(cand={cand_score}, kw={matched})")

    print(f"\n  1차 통과 후보: {len(candidates)}건")

    print(f"\n[3/3] Claude fit 스코어링 ({CLAUDE_MODEL})...")
    rows = []
    for i, c in enumerate(candidates, 1):
        it = c["item"]
        rcept_no = it.get("rcept_no", "")
        corp_name = it.get("corp_name", "?")
        fit = claude_fit_score(corp_name, it.get("report_nm", ""), c["text"])
        print(f"  [{i}/{len(candidates)}] {corp_name} → fit {fit['fit_score']}")

        row = {
            "rcept_no": rcept_no,
            "corp_code": it.get("corp_code", ""),
            "corp_name": corp_name,
            "report_nm": it.get("report_nm", ""),
            "rcept_dt": it.get("rcept_dt", ""),
            "matched_keywords": ", ".join(c["matched"]),
            "candidate_score": c["candidate_score"],
            "fit_score": fit["fit_score"],
            "industry": fit["업종"],
            "australia_basis": fit["호주_연관_근거"],
            "approach_angle": fit["추천_접근앵글"],
            "hold_reason": fit["보류사유"],
            "dart_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
        }
        save_lead(row)
        rows.append(row)

    if not rows:
        print("\n새 리드 후보가 없습니다.")
        return

    rows_sorted = write_csv(rows)
    print(f"\n✅ candidates.csv 작성 완료 ({len(rows_sorted)}건, fit_score 내림차순)")

    if SEND_TELEGRAM:
        notify_telegram(rows_sorted)

    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
