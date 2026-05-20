import os
import re
import requests
import zipfile
import io
from dotenv import load_dotenv

load_dotenv()

DART_API_KEY = os.getenv("DART_API_KEY")


def get_document_text(rcept_no):
    """DART 공시 원문 텍스트를 가져온다"""

    # 1단계: 공시 문서번호 조회
    url = "https://opendart.fss.or.kr/api/document.xml"
    params = {
        "crtfc_key": DART_API_KEY,
        "rcept_no": rcept_no,
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"API 호출 실패: {response.status_code}")
        return None

    # ZIP 파일로 온다
    try:
        z = zipfile.ZipFile(io.BytesIO(response.content))
    except zipfile.BadZipFile:
        print(f"ZIP 파일이 아님 (에러 응답일 수 있음)")
        print(f"응답 앞 200자: {response.text[:200]}")
        return None

    # ZIP 안에 있는 XML 파일 읽기
    filenames = z.namelist()
    print(f"ZIP 안의 파일들: {filenames}")

    # 첫 번째 XML 파일 읽기
    xml_content = z.read(filenames[0]).decode("utf-8", errors="replace")

    # HTML/XML 태그 제거해서 순수 텍스트만 추출
    text = re.sub(r"<[^>]+>", " ", xml_content)
    # 연속 공백 정리
    text = re.sub(r"\s+", " ", text).strip()

    return text


if __name__ == "__main__":
    # 아까 찾았던 실제 공시로 테스트
    test_rcept_no = "20260430902093"  # 나노씨엠에스
    print(f"공시 원문 가져오기 테스트: {test_rcept_no}")
    print("=" * 50)
    print()

    text = get_document_text(test_rcept_no)

    if text:
        print(f"원문 길이: {len(text)}자")
        print()
        print("--- 원문 앞 2000자 미리보기 ---")
        print(text[:2000])
        print()
        print("--- 원문 뒤 1000자 미리보기 ---")
        print(text[-1000:])
    else:
        print("원문을 가져오지 못했습니다.")