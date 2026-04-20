"""RAGAS v0.4 API 검증 — metric.ascore() 동작 확인."""

import sys


def check_ragas_version() -> bool:
    """RAGAS 버전 확인 (0.4.x 필수)."""
    import ragas

    version = ragas.__version__
    print(f"[ragas] 설치 버전: {version}")
    major_minor = tuple(int(x) for x in version.split(".")[:2])
    if major_minor[0] == 0 and major_minor[1] >= 4:
        print("[ragas] v0.4 확인 완료")
        return True
    print(f"[ragas] 경고: v0.4가 아닙니다 (현재: {version})")
    return False


def check_metrics_import() -> bool:
    """v0.4 메트릭 임포트 테스트."""
    print("\n--- v0.4 메트릭 임포트 테스트 ---")
    available_metrics = []

    metric_imports = [
        ("Faithfulness", "ragas.metrics.collections"),
        ("ResponseRelevancy", "ragas.metrics.collections"),
        ("ContextPrecision", "ragas.metrics.collections"),
        ("ContextRecall", "ragas.metrics.collections"),
    ]
    import importlib

    for name, module_path in metric_imports:
        try:
            mod = importlib.import_module(module_path)
            getattr(mod, name)
            available_metrics.append(name)
            print(f"  [OK] from {module_path} import {name}")
        except (ImportError, AttributeError) as e:
            print(f"  [FAIL] {name}: {e}")

    print(f"\n사용 가능한 메트릭: {available_metrics}")
    return len(available_metrics) >= 2


def check_sample_data() -> bool:
    """v0.4 SingleTurnSample 구조 확인."""
    print("\n--- v0.4 SingleTurnSample 구조 테스트 ---")
    try:
        from ragas.dataset_schema import SingleTurnSample

        sample = SingleTurnSample(
            user_input="청년 주거 정책에는 어떤 것이 있나요?",
            response="청년 전세임대, 청년 매입임대, 청년 월세 지원 등이 있습니다.",
            retrieved_contexts=[
                "청년 전세임대는 LH에서 운영하는 주거 지원 정책으로, 만 19~39세 청년이 대상입니다.",
                "청년 매입임대는 시세의 40~50%로 거주할 수 있는 공공임대주택입니다.",
            ],
            reference="청년 주거 정책으로는 청년 전세임대, 청년 매입임대, 청년 월세 지원이 있습니다.",
        )
        print("  [OK] SingleTurnSample 생성 성공")
        print(f"  user_input: {sample.user_input[:50]}...")
        print(f"  response: {sample.response[:50]}...")
        print(f"  contexts: {len(sample.retrieved_contexts)}개")
        return True
    except ImportError:
        print("  [FAIL] SingleTurnSample import 실패")
        try:
            from ragas import EvaluationDataset  # noqa: F401

            print("  [INFO] EvaluationDataset은 사용 가능")
        except ImportError:
            pass
        return False
    except Exception as e:
        print(f"  [FAIL] SingleTurnSample 생성 실패: {e}")
        return False


def check_ascore_method() -> bool:
    """metric.ascore() 메서드 존재 확인 (실제 LLM 호출 없이)."""
    print("\n--- metric.ascore() 메서드 확인 ---")
    try:
        from ragas.metrics.collections import Faithfulness

        metric = Faithfulness()
        has_ascore = hasattr(metric, "ascore") or hasattr(metric, "single_turn_ascore")
        has_score = hasattr(metric, "score") or hasattr(metric, "single_turn_score")

        print(f"  ascore 메서드: {'있음' if has_ascore else '없음'}")
        print(f"  score 메서드: {'있음' if has_score else '없음'}")

        all_methods = [m for m in dir(metric) if "score" in m.lower()]
        print(f"  score 관련 메서드: {all_methods}")
        return has_ascore or has_score
    except Exception as e:
        print(f"  [FAIL] {e}")
        return False


def check_evaluate_function() -> bool:
    """ragas.evaluate() 함수 확인."""
    print("\n--- ragas.evaluate() 함수 확인 ---")
    try:
        from ragas import evaluate  # noqa: F401

        print("  [OK] from ragas import evaluate")
        return True
    except ImportError as e:
        print(f"  [FAIL] {e}")
        return False


def main() -> None:
    print("=" * 60)
    print("RAGAS v0.4 API 검증")
    print("=" * 60)

    results = {}
    results["version"] = check_ragas_version()
    results["metrics"] = check_metrics_import()
    results["sample_data"] = check_sample_data()
    results["ascore"] = check_ascore_method()
    results["evaluate"] = check_evaluate_function()

    print("\n" + "=" * 60)
    print("검증 결과 요약")
    print("=" * 60)
    all_pass = True
    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check:20s}: {status}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\n모든 검증 통과. RAGAS v0.4 사용 준비 완료.")
    else:
        print("\n일부 검증 실패. 위 로그를 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
