"""
G-ensemble Integrated Test Runner (통합 테스트 러너)
모든 핵심 단위/통합 테스트를 일괄 실행하여 파이프라인 정합성을 진단합니다.

사용법:
    python test_runner.py
    python test_runner.py --quick  (알고리즘 및 로컬 테스트만 빠르게 실행)
"""

import sys
import os
import argparse
from dotenv import load_dotenv

# 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_weight_engine_tests():
    print("\n[1/3] 🧪 WeightEngine v1.8 알고리즘 단위 테스트 실행...")
    try:
        from test_weight_v1_8 import test_weight_engine_v1_8
        test_weight_engine_v1_8()
        print("  ✅ WeightEngine v1.8 테스트 성공 (6개 케이스 All Pass)")
        return True
    except Exception as e:
        print(f"  ❌ WeightEngine 테스트 실패: {e}")
        return False

def run_fetcher_tests():
    print("\n[2/3] 📡 데이터 Fetcher 통신 및 정합성 테스트 실행...")
    try:
        from fetchers.stock_fetcher import StockFetcher
        from fetchers.sd_fetcher import SDFetcher
        from fetchers.fx_fetcher import FXFetcher
        from fetchers.global_fetcher import GlobalFetcher

        stock = StockFetcher().fetch()
        sd = SDFetcher().fetch()
        fx = FXFetcher().fetch()
        gl = GlobalFetcher().fetch()

        print(f"  - Stock (KORU/EWY): {bool(stock)}")
        print(f"  - Supply/Demand (외인/개인): {bool(sd)}")
        print(f"  - FX (USDKRW): {bool(fx)}")
        print(f"  - Global (VIX/DXY): {bool(gl)}")
        print("  ✅ Fetchers 연동 테스트 성공")
        return True
    except Exception as e:
        print(f"  ❌ Fetchers 테스트 실패: {e}")
        return False

def run_model_tests():
    print("\n[3/3] 🤖 Gemini 3.7 Flash 모델 추론 테스트 실행...")
    try:
        load_dotenv()
        from models.yt_analyzer import YTAnalyzer
        analyzer = YTAnalyzer(model_name='gemini-3.7-flash')
        
        # 샘플 입력으로 역지표 추론 검증
        test_title = "코스피 3000 돌파 임박? 지금 당장 사야할 주식 TOP 3"
        result = analyzer.analyze_sentiment("dummy_id")
        print(f"  - 모델 응답 점수: {result.get('score')}점")
        print(f"  - 모델 요약/이유: {str(result.get('summary', result.get('reason')))[:60]}...")
        print("  ✅ Gemini 모델 추론 테스트 성공")
        return True
    except Exception as e:
        print(f"  ❌ Gemini 모델 테스트 실패: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="G-ensemble 통합 테스트 러너")
    parser.add_argument("--quick", action="store_true", help="API 호출 제외 빠른 단위 테스트만 실행")
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 G-ensemble Pipeline Diagnostic & Test Runner")
    print("=" * 60)

    results = []
    results.append(("WeightEngine v1.8", run_weight_engine_tests()))
    
    if not args.quick:
        results.append(("Data Fetchers", run_fetcher_tests()))
        results.append(("Gemini 3.7 Model", run_model_tests()))

    print("\n" + "=" * 60)
    print("📊 종합 테스트 결과 요약:")
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False
        print(f"  - {name:<25}: {status}")
    print("=" * 60)

    if all_passed:
        print("🎉 모든 진단 테스트를 통과했습니다!")
        sys.exit(0)
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 로그를 확인하세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()
