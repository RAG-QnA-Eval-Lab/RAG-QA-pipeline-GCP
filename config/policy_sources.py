POLICY_SOURCES = {
    "youthgo": {
        "name": "온통청년",
        "base_url": "https://www.youthcenter.go.kr",
        "method": "crawl",
        "priority": 5,
    },
    "data_portal": {
        "name": "공공데이터포털",
        "base_url": "https://api.odcloud.kr/api",
        "method": "api",
        "priority": 5,
    },
    "kosaf": {
        "name": "한국장학재단",
        "base_url": "https://www.kosaf.go.kr",
        "method": "crawl",
        "priority": 4,
    },
    "pdf_reports": {
        "name": "정부 발행 PDF 보고서",
        "base_url": "",
        "method": "manual",
        "priority": 3,
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
