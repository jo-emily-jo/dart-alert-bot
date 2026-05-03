import sqlite3
from datetime import datetime

DB_PATH = "seen_disclosures.db"

def init_db():
    """DB와 테이블을 만든다. 이미 있으면 건너뜀."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS disclosures (
        -- 기본 식별 정보 (V1에서 채움)
        rcept_no        TEXT PRIMARY KEY,
        corp_name       TEXT NOT NULL,
        stock_code      TEXT,
        report_nm       TEXT NOT NULL,
        rcept_dt        TEXT NOT NULL,
        dart_url        TEXT,

        -- 계약 상세 정보 (V2에서 채울 예정)
        contract_name   TEXT,
        contract_amount INTEGER,
        recent_revenue  INTEGER,
        contract_to_revenue_ratio REAL,
        counterparty    TEXT,
        contract_start_date TEXT,
        contract_end_date   TEXT,

        -- 정정공시 여부 (V1에서 부분 체크)
        is_correction   INTEGER DEFAULT 0,

        -- 원문 텍스트 (V2에서 채울 예정)
        raw_text        TEXT,

        -- Claude 요약 결과 (V1에서 채움)
        summary         TEXT,

        -- 메타 정보
        matched_keyword TEXT,
        alerted_at      TEXT,
        created_at      TEXT DEFAULT (datetime('now', 'localtime'))
    )
    """)

    # 나중에 "같은 회사가 반복 수주했는지" 빠르게 찾기 위한 인덱스
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_corp_name
    ON disclosures(corp_name)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_rcept_dt
    ON disclosures(rcept_dt)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_counterparty
    ON disclosures(counterparty)
    """)

    conn.commit()
    conn.close()
    print("DB 초기화 완료!")

def is_seen(rcept_no):
    """이미 본 공시인지 확인"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM disclosures WHERE rcept_no = ?", (rcept_no,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def save_disclosure(item, matched_keyword=""):
    """공시를 DB에 저장"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    rcept_no = item.get("rcept_no", "")
    report_nm = item.get("report_nm", "")

    # 정정공시 여부: 제목에 [정정] 이 들어있으면 1
    is_correction = 1 if "[정정]" in report_nm else 0

    # DART 공시 원문 URL
    dart_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"

    cursor.execute("""
    INSERT OR IGNORE INTO disclosures
        (rcept_no, corp_name, stock_code, report_nm, rcept_dt,
         dart_url, is_correction, matched_keyword)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rcept_no,
        item.get("corp_name", ""),
        item.get("stock_code", ""),
        report_nm,
        item.get("rcept_dt", ""),
        dart_url,
        is_correction,
        matched_keyword,
    ))

    conn.commit()
    conn.close()

def get_past_disclosures(corp_name, limit=5):
    """같은 회사의 과거 공시 이력 조회 (반복 수주 추적용)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT rcept_dt, report_nm, contract_amount, counterparty
    FROM disclosures
    WHERE corp_name = ?
    ORDER BY rcept_dt DESC
    LIMIT ?
    """, (corp_name, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print()
    print("테이블 구조 확인:")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(disclosures)")
    for col in cursor.fetchall():
        print(f"  {col[1]:30s} {col[2]:10s} {'(PK)' if col[5] else ''}")
    conn.close()
