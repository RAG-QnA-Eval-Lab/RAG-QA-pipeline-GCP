POLICY_SOURCES = {
    "youthgo": {
        "name": "온통청년",
        "base_url": "https://www.youthcenter.go.kr",
        "method": "crawl",
        "priority": 5,
        "endpoints": {
            "search_api": "/pubot/search/portalPolicySearch",
            "open_api": "/opi/youthPlcyList.do",
            "search_page": "/youthPolicy/ythPlcyTotalSearch",
        },
        "notes": "내부 API는 세션쿠키(ygt JWT)+CSRF 필요. Open API는 회원가입+키 승인 필요(XML).",
    },
    "data_portal": {
        "name": "공공데이터포털 (온통청년 Open API 경유)",
        "base_url": "https://www.youthcenter.go.kr",
        "method": "api",
        "priority": 5,
        "endpoints": {
            "youth_policy": "/go/ythip/getPlcy",
        },
        "auth_param": "apiKeyNm",
        "pagination": {"page_param": "pageNum", "size_param": "pageSize", "default_size": 100},
        "total_count": 2185,
        "categories": {
            "lclsfNm": ["일자리", "주거", "교육", "금융･복지･문화", "참여·권리"],
        },
        "notes": "서비스 15143273 (LINK 타입). rtnType=json 필수. 필드 60개.",
    },
    "kosaf": {
        "name": "한국장학재단",
        "base_url": "https://www.kosaf.go.kr",
        "method": "crawl",
        "priority": 4,
        "endpoints": {
            "scholarship_base": "/ko/scholar.do",
            "tuition_support": "/ko/tuition.do",
        },
        "page_patterns": [
            "scholarship05_11_01",
            "scholarship05_11_02",
            "scholarship05_12_01",
            "scholarship05_12_02",
            "scholarship05_13_01",
            "scholarship05_13_02",
            "scholarship05_14_01",
            "scholarship05_14_02",
            "scholarship05_15_01",
        ],
        "notes": "SSR HTML, BeautifulSoup 파싱. robots.txt 전면 허용. k-skill 정규화 스키마 참고.",
    },
    "pdf_reports": {
        "name": "정부 발행 PDF 보고서",
        "base_url": "",
        "method": "manual",
        "priority": 3,
        "notes": "수동 수집 후 PyMuPDF/pdfplumber 파싱.",
    },
}

POLICY_CATEGORIES = [
    "housing",
    "employment",
    "startup",
    "education",
    "welfare",
    "finance",
]

KOSAF_SCHEMA_REF = {
    "source": "NomaDamas/k-skill korean-scholarship-search",
    "fields": {
        "name": "장학금명",
        "organization": {"type": "school|foundation|government|local-government|company|other", "name": "운영기관명"},
        "eligibility": {
            "school_names": "대상 학교",
            "student_levels": "학부/석사/박사",
            "grade_years": "학년",
            "majors": "전공",
            "gpa_min": "최소 학점",
            "income_band_min": "소득분위 하한",
            "income_band_max": "소득분위 상한",
        },
        "deadline": {"start": "시작일", "end": "종료일", "status": "open|upcoming|closed|unknown"},
        "amount": {"annual_krw": "연간 금액", "per_semester_krw": "학기당 금액", "text": "원문"},
    },
}
