import pandas as pd
import numpy as np
from datetime import datetime

class WeightEngine:
    """
    G-Ensemble v1.9 Core Algorithm Engine
    수급, 반도체(SOXX), 변동성(KORU), 인간 지표, 환율 및 V/O 초단기 수급 동적 폴백 로직을 관리합니다.
    """

    def __init__(self):
        # 1. 기본 가중치 (Base Weights - Standard Mode)
        self.base_weights = {
            "F": 0.35,     # 외국인 수급 (현물+선물)
            "SOXX": 0.15,  # 글로벌 반도체 지수 (코스피 선행)
            "K": 0.20,     # KORU ETF (시장 변동성)
            "H": 0.20,     # 인간 지표 (유튜브 역발상)
            "R": 0.10      # 개인 수급 (역지표)
        }
        
        # 2. 임계값 설정 (Thresholds for Linear Interpolation)
        self.thresholds = {
            "F": 5000,      # +/- 5,000억 (Extreme)
            "SOXX": 3.0,    # +/- 3.0% (Extreme)
            "K": 4.5,       # +/- 4.5% (Extreme)
            "R": 3000       # +/- 3,000억 (Extreme)
        }

    def clamp(self, val, min_val=-1.0, max_val=1.0):
        """값을 주어진 범위 내로 제한합니다."""
        return max(min(val, max_val), min_val)

    def get_market_label(self, score):
        """최종 스코어(S)에 따른 7단계 시장 판정 라벨을 반환합니다."""
        if score >= 0.50: return "Strong Bullish"
        if score >= 0.35: return "Bullish"
        if score >= 0.15: return "Slightly Bullish"
        if score > -0.15: return "Neutral"
        if score > -0.35: return "Slightly Bearish"
        if score > -0.50: return "Bearish"
        return "Strong Bearish"

    def get_indicator_label(self, val):
        """개별 지표의 스코어에 따른 라벨을 반환합니다."""
        abs_val = abs(val)
        sign = "Bull" if val > 0 else "Bear"
        if val == 0: return "Neutral"
        
        if abs_val >= 1.0: return f"Extreme {sign}"
        if abs_val >= 0.7: return f"Standard {sign}"
        if abs_val >= 0.3: return f"Slight {sign}"
        return "Neutral"

    def calculate_fx_alpha(self, fx_data):
        """
        4.1 환율 보정 (Alpha_FX)
        환율은 시장의 하방 압력으로만 작용 (0 또는 음수).
        최근 60일 Z-score 기준 동적 판정 적용.
        """
        usd_krw = fx_data.get('USDKRW', 1350)
        zscore = fx_data.get('USDKRW_zscore', 0.0)
        
        alpha = 0.0
        desc = f"실시간 환율 {usd_krw:,.2f}원 (Z: {zscore:+.2f})"
        
        if zscore >= 2.5:
            alpha = -0.5   # 극도 위험
            desc += " [위험]"
        elif zscore >= 1.5:
            alpha = -0.25  # 급등 경고
            desc += " [주의]"
        elif zscore >= 0.5:
            alpha = -0.1   # 상승 주의
            desc += " [경고]"
        else:
            alpha = 0.0    # 안정 상태
            desc += " [안정]"
            
        return alpha, desc

    def calculate_ensemble(self, yt_data, stock_data, sd_data, fx_data, global_data={}):
        """
        v1.9 통합 앙상블 스코어 산출 (V/O 초단기 수급 동적 폴백 포함)
        """
        results = {}
        
        # 상태 취합
        is_holiday = stock_data.get('is_holiday', False) or sd_data.get('is_holiday', False)
        is_bullet = stock_data.get('is_bullet', False) or fx_data.get('is_bullet', False)
        
        # 주말 괴리 발생 시 EWY로 대체
        is_deviation = stock_data.get('deviation_flag', False)
        if is_deviation:
            koru_chg = stock_data.get('EWY', {}).get('pct_change', 0)
        else:
            koru_chg = stock_data.get('KORU', {}).get('pct_change', 0)

        vix_info = global_data.get('VIX', {})
        vix_val = vix_info.get('last_close', 0)
        
        f_raw = sd_data.get('foreign', 0)
        f_futures = sd_data.get('foreign_futures', 0)
        
        # --- [모드 결정: Dynamic Chains & V/O Fallback] ---
        current_mode = "Standard"
        weights = self.base_weights.copy()
        
        # V/O 모드 트리거 조건:
        # 1) KORU 절대 변동률 6% 이상
        # 2) 09:10 장초반 실시간 외인 수급 폭증 (현물 2,500억+ 또는 선물 2,500억+)
        # 3) VIX 25 이상
        is_vo_trigger = (abs(koru_chg) >= 6.0) or (abs(f_raw) >= 2500) or (abs(f_futures) >= 2500) or (vix_val >= 25)
        
        if is_vo_trigger:
            current_mode = "Volatility Overdrive (V/O)"
            # 초단기 실시간 수급 집중 폴백 (외인 50% + 개인 20% + KORU 20% + 인간지표 10%, 전일 SOXX는 0%)
            weights = {"F": 0.50, "R": 0.20, "K": 0.20, "H": 0.10, "SOXX": 0.0}
            
        # 크라이시스 모드 (장초반 급락 -6% 이하 또는 VIX 30 이상 폭등)
        if koru_chg <= -6.0 or vix_val >= 30:
            current_mode = "Crisis Mode"
            weights = {"F": 0.70, "K": 0.20, "R": 0.05, "H": 0.05, "SOXX": 0.0}
        
        # --- [지표별 스코어 산출 (Normalization)] ---

        # 1. 외국인 수급 (F)
        f_score = self.clamp(f_raw / self.thresholds['F'])
        f_adj = 1.0
        if f_raw > 0 and f_futures > 0: f_adj = 1.2
        elif f_raw < 0 and f_futures < 0: f_adj = 1.5
        elif f_raw > 0 and f_futures < 0: f_adj = 0.7
        elif f_raw < 0 and f_futures > 0: f_adj = 0.8
        
        f_val = f_score * f_adj
        results['foreign'] = {
            "val": f_val,
            "weight": weights['F'],
            "label": self.get_indicator_label(f_val),
            "desc": f"외인 수급: {f_raw:,}억 (선물 {f_futures:+,}억, 보정 x{f_adj})"
        }

        # 2. 글로벌 반도체 지수 (SOXX)
        soxx_info = global_data.get('SOXX', {})
        soxx_chg = soxx_info.get('pct_change', 0.0)
        soxx_val = self.clamp(soxx_chg / self.thresholds['SOXX'])
        results['soxx'] = {
            "val": soxx_val,
            "weight": weights.get('SOXX', 0.0),
            "label": self.get_indicator_label(soxx_val),
            "desc": f"반도체(SOXX): {soxx_chg:+.2f}%"
        }

        # 3. KORU (K) - 시장 변동성
        k_val = self.clamp(koru_chg / self.thresholds['K'])
        k_desc = f"EWY 대체: {koru_chg:+.2f}%" if is_deviation else f"KORU 변동: {koru_chg:+.2f}%"
        results['koru'] = {
            "val": k_val,
            "weight": weights['K'],
            "label": self.get_indicator_label(k_val),
            "desc": k_desc
        }

        # 4. 인간 지표 (H) - 역발상 로직
        yt_score = yt_data.get('score', 50)
        h_val = 0.0
        if not (40 <= yt_score <= 60):  # Dead-zone (40~60점) 제외
            h_val = -((yt_score - 50) / 50.0)
        
        results['youtube'] = {
            "val": h_val,
            "weight": weights['H'],
            "label": self.get_indicator_label(h_val),
            "desc": f"인간 지표: {yt_score}점 (역발상)"
        }

        # 5. 개인 수급 (R) - 역지표
        r_raw = sd_data.get('individual', 0)
        r_val = self.clamp(-r_raw / self.thresholds['R'])  # 개인이 사면 음수
        results['retail'] = {
            "val": r_val,
            "weight": weights['R'],
            "label": self.get_indicator_label(r_val),
            "desc": f"개인 수급: {r_raw:,}억 (역지표)"
        }

        # --- [최종 합산 및 보정] ---
        
        # 가중 합산
        base_sum = sum(results[k]['val'] * results[k]['weight'] for k in results if k in ['foreign', 'soxx', 'koru', 'youtube', 'retail'])
        
        # 환율 보정 (Alpha_FX)
        fx_alpha, fx_desc = self.calculate_fx_alpha(fx_data)
        
        results['fx'] = {
            "val": fx_alpha,
            "weight": 0.0,
            "label": "Warning" if fx_alpha < 0 else "Stable",
            "desc": fx_desc
        }

        final_score = base_sum + fx_alpha
        
        # 오버슈팅 방지 (Slightly Bullish 이고 유튜브 낙관적이면 Neutral 조정)
        if 0.15 <= final_score < 0.35 and h_val < 0:
            final_score = 0.0
            results['overshooting_adj'] = True

        return {
            "final_score": round(final_score, 4),
            "mode": current_mode,
            "label": self.get_market_label(final_score),
            "details": results,
            "fx_alpha": fx_alpha,
            "signal": "BUY" if final_score > 0.15 else "SELL" if final_score < -0.15 else "HOLD",
            "is_holiday": is_holiday,
            "is_bullet": is_bullet
        }

