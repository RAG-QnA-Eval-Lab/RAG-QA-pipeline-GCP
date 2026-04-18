"""온통청년 내부 검색 API를 사용하여 청년 정책 50건 수집 테스트."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE_URL = "https://www.youthcenter.go.kr"
SEARCH_PAGE = f"{BASE_URL}/youthPolicy/ythPlcyTotalSearch"
SEARCH_API = f"{BASE_URL}/pubot/search/portalPolicySearch"

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "policies" / "raw"
OUTPUT_FILE = OUTPUT_DIR / "youthgo_sample.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": SEARCH_PAGE,
    "Origin": BASE_URL,
}


def get_session(client: httpx.Client) -> str | None:
    """검색 페이지에 접속하여 세션 쿠키와 XSRF 토큰을 획득."""
    resp = client.get(SEARCH_PAGE, follow_redirects=True)
    resp.raise_for_status()
    xsrf = client.cookies.get("XSRF-TOKEN")
    print(f"[session] status={resp.status_code}, cookies={list(client.cookies.jar)}")
    print(f"[session] XSRF-TOKEN={'있음' if xsrf else '없음'}")
    return xsrf


def search_policies(client: httpx.Client, xsrf: str | None, page: int = 1, count: int = 50) -> dict:
    """내부 검색 API로 정책 목록 조회."""
    payload = {
        "currentPage": page,
        "listCount": count,
        "searchWord": "",
        "categoryCode": "",
        "sido": "",
        "sigoongu": "",
        "sortOrder": "recent",
    }
    headers = dict(HEADERS)
    if xsrf:
        headers["X-XSRF-TOKEN"] = xsrf

    time.sleep(2)
    resp = client.post(SEARCH_API, json=payload, headers=headers)
    print(f"[search] status={resp.status_code}, content-type={resp.headers.get('content-type')}")

    if resp.status_code != 200:
        print(f"[search] response body (first 500 chars): {resp.text[:500]}")
        resp.raise_for_status()

    return resp.json()


def normalize_policy(raw: dict, idx: int) -> dict:
    """API 응답의 개별 정책을 정규화된 스키마로 변환."""
    policy_id = raw.get("DOCID") or raw.get("plcyId") or f"youthgo_{idx}"
    return {
        "policy_id": policy_id,
        "title": raw.get("PLCY_NM") or raw.get("plcyNm") or "",
        "category": raw.get("BSC_PLAN_PLCY_WAY_NO") or "",
        "region": raw.get("STDG_TOKEN") or "",
        "organization": raw.get("SPRVSN_INST_CD_NM") or "",
        "operating_org": raw.get("OPER_INST_CD_NM") or "",
        "summary": raw.get("PLCY_EXPLN_CN") or "",
        "support_content": raw.get("PLCY_SPRT_CN") or "",
        "target_age_min": raw.get("SPRT_TRGT_MIN_AGE"),
        "target_age_max": raw.get("SPRT_TRGT_MAX_AGE"),
        "apply_period": raw.get("APLY_PRD_SE_CD") or "",
        "biz_period_start": raw.get("BIZ_PRD_BGNG_YMD") or "",
        "biz_period_end": raw.get("BIZ_PRD_END_YMD") or "",
        "status": raw.get("PLCY_STTS_CD") or "",
        "marriage_status": raw.get("MRG_STTS_NM") or "",
        "reference_url": raw.get("REF_URL_ADDR1") or "",
        "apply_url": raw.get("APLY_URL_ADDR") or "",
        "source": "youthgo",
        "source_url": f"{BASE_URL}/youthPolicy/policyDetail?plcyId={policy_id}",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "raw_data": raw,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        print("=== 온통청년 정책 수집 테스트 (50건) ===\n")

        print("[1/3] 세션 획득 중...")
        xsrf = get_session(client)

        print("\n[2/3] 정책 검색 API 호출 (50건)...")
        result = search_policies(client, xsrf, count=50)

        search_result = result.get("searchResult", {})
        policies_raw = search_result.get("youthpolicy", result.get("result", result.get("data", [])))
        if isinstance(policies_raw, dict):
            policies_raw = policies_raw.get("list", policies_raw.get("content", []))

        total_count = result.get("totalCount", result.get("total", len(policies_raw)))
        print(f"[search] 전체 정책 수: {total_count}, 수신 건수: {len(policies_raw)}")

        if not policies_raw:
            print("\n[!] 정책 데이터를 찾을 수 없습니다. API 응답 구조를 확인합니다.")
            print(f"응답 키: {list(result.keys())}")
            if len(json.dumps(result, ensure_ascii=False)) < 2000:
                print(f"응답 전체:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
            else:
                print(f"응답 일부:\n{json.dumps(result, ensure_ascii=False, indent=2)[:2000]}")

            OUTPUT_FILE.with_suffix(".raw.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"\n원본 응답 저장: {OUTPUT_FILE.with_suffix('.raw.json')}")
            return

        print(f"\n[3/3] 정규화 및 저장...")
        policies = [normalize_policy(p, i) for i, p in enumerate(policies_raw)]

        output = {
            "source": "youthgo",
            "api_endpoint": SEARCH_API,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "total_available": total_count,
            "collected_count": len(policies),
            "policies": policies,
        }

        OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"저장 완료: {OUTPUT_FILE}")
        print(f"수집 건수: {len(policies)}")

        if policies:
            sample = policies[0]
            print(f"\n--- 샘플 (첫 번째 정책) ---")
            print(f"  policy_id:    {sample['policy_id']}")
            print(f"  title:        {sample['title']}")
            print(f"  organization: {sample['organization']}")
            print(f"  apply_period: {sample['apply_period']}")
            print(f"  summary:      {sample['summary'][:100]}...")
            print(f"  support:      {sample['support_content'][:100]}...")


if __name__ == "__main__":
    main()
