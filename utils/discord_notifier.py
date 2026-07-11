import requests
from datetime import datetime, timezone, timedelta

class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.KST = timezone(timedelta(hours=9))

    def _truncate(self, text, limit):
        """Discord Embed 필드 글자수 제한 대응"""
        if not text or len(text) <= limit:
            return text or "N/A"
        return text[:limit - 3] + "..."

    def _signal_style(self, signal):
        """신호별 이모지 및 색상 반환"""
        styles = {
            "BUY":  {"emoji": "🚀", "color": 0x00D26A, "action": "매수 우위"},
            "SELL": {"emoji": "🆘", "color": 0xFF4757, "action": "매도 우위"},
            "HOLD": {"emoji": "⚖️", "color": 0x747D8C, "action": "관망"},
        }
        return styles.get(signal, styles["HOLD"])

    def _build_indicator_value(self, indicator, name=""):
        """지표 필드 값을 가독성 있는 포맷으로 구성"""
        val = indicator.get('val', 0)
        label = indicator.get('label', 'N/A')
        desc = indicator.get('desc', 'N/A')
        
        # 핵심 수치만 추출 (desc에서 콜론 이후 부분)
        if ':' in desc:
            detail = desc.split(':', 1)[1].strip()
        else:
            detail = desc
            
        # 방향 및 경고 이모지 매핑
        if "환율" in name or label in ["Stable", "Warning"]:
            # 환율 지표 전용 처리
            if val == 0.0:
                arrow = "🟢"
            elif val == -0.1:
                arrow = "🟡"
            elif val == -0.25:
                arrow = "🟠"
            else:
                arrow = "🔴"
            return f"{arrow} {detail}\n패널티 `{val:+.2f}`"
        else:
            # 일반 수급 및 KORU 지표
            if val > 0.3:
                arrow = "🟢"
            elif val > 0:
                arrow = "🔵"
            elif val > -0.3:
                arrow = "🟡"
            else:
                arrow = "🔴"
            return f"{arrow} {detail}\n`{label}` ({val:+.2f})"

    def _build_embed_header(self, report_data, style):
        """Embed 1: 헤더 + 지표 스냅샷 대시보드"""
        now = datetime.now(self.KST).strftime('%Y-%m-%d %H:%M')
        signal = report_data.get('signal', 'HOLD')
        score = report_data.get('final_score', 0)
        mode = report_data.get('mode', 'Standard')
        label = report_data.get('label', 'Neutral')
        details = report_data.get('details', {})
        
        is_holiday = report_data.get('is_holiday', False)
        is_bullet = report_data.get('is_bullet', False)
        
        # 상태 배지
        if is_holiday:
            status = "🏖️ 휴장"
        elif is_bullet:
            status = "🔫 이상감지"
        else:
            status = "✅ 정상"

        # 헤더 description
        desc_lines = [
            f"📅 **{now}** │ {status}",
            f"",
            f"**{style['emoji']} 최종 판정: {label}**",
            f"스코어 `{score:+.4f}` │ 신호 **{signal}** │ 모드 `{mode}`",
        ]

        # 지표 필드 (2열 inline 그리드)
        fields = []
        
        # Row 1: 외인 | KORU
        if 'foreign' in details:
            fields.append({
                "name": "🏦 외인 수급",
                "value": self._build_indicator_value(details['foreign'], name="foreign"),
                "inline": True
            })
        if 'koru' in details:
            fields.append({
                "name": "🌏 선행지표 (KORU)",
                "value": self._build_indicator_value(details['koru'], name="koru"),
                "inline": True
            })
        # 줄바꿈용 빈 필드
        fields.append({"name": "\u200b", "value": "\u200b", "inline": False})
        
        # Row 2: 개인 | 환율
        if 'retail' in details:
            fields.append({
                "name": "👤 개인 수급",
                "value": self._build_indicator_value(details['retail'], name="retail"),
                "inline": True
            })
        if 'fx' in details:
            fields.append({
                "name": "💱 환율 보정",
                "value": self._build_indicator_value(details['fx'], name="fx"),
                "inline": True
            })
        # 줄바꿈용 빈 필드
        fields.append({"name": "\u200b", "value": "\u200b", "inline": False})
        
        # Row 3: 인간지표 (전체 폭)
        if 'youtube' in details:
            yt = details['youtube']
            yt_desc = yt.get('desc', 'N/A')
            yt_val = yt.get('val', 0)
            yt_label = yt.get('label', 'N/A')
            
            if yt_val > 0:
                yt_arrow = "🟢"
                yt_note = "유튜버 비관 → 역발상 매수 신호"
            elif yt_val < 0:
                yt_arrow = "🔴"
                yt_note = "유튜버 낙관 → 역발상 과열 경고"
            else:
                yt_arrow = "🟡"
                yt_note = "중립 구간 (Dead-zone)"
            
            fields.append({
                "name": "🎭 인간지표 (역지표)",
                "value": f"{yt_arrow} {yt_desc}\n`{yt_label}` ({yt_val:+.2f}) — {yt_note}",
                "inline": False
            })

        embed = {
            "title": f"{style['emoji']} GENSE KOSPI 방향 예측 레포트",
            "description": "\n".join(desc_lines),
            "color": style['color'],
            "fields": fields,
        }
        
        return embed

    def _build_embed_analysis(self, report_data, style):
        """Embed 2: 종합 진단 (AI 분석 본문)"""
        analysis = report_data.get('analysis', {})
        
        one_liner = analysis.get('one_liner', '분석 데이터 없음')
        market_summary = self._truncate(analysis.get('market_summary', 'N/A'), 1024)
        yt_insight = self._truncate(analysis.get('yt_insight', 'N/A'), 1024)
        
        fields = []
        
        # 시장 서머리
        fields.append({
            "name": "🔍 시장 서머리",
            "value": market_summary,
            "inline": False
        })
        
        # 핵심 테마 (최대 3개)
        for i, item in enumerate(analysis.get('key_analysis', [])[:3]):
            title = item.get('title', f'테마 {i+1}')
            content = self._truncate(item.get('content', 'N/A'), 900)
            fields.append({
                "name": f"📌 {title}",
                "value": content,
                "inline": False
            })
        
        # 유튜브 인사이트
        fields.append({
            "name": "🎭 유튜브 인사이트",
            "value": yt_insight,
            "inline": False
        })
        
        embed = {
            "title": "📈 종합 진단",
            "description": f"**\"{one_liner}\"**",
            "color": style['color'],
            "fields": fields,
        }
        
        return embed

    def _build_embed_strategy(self, report_data, style):
        """Embed 3: 대응 전략 + 영상 출처"""
        analysis = report_data.get('analysis', {})
        strategy = analysis.get('strategy', {})
        
        position = strategy.get('position', '분석 불가')
        guides = strategy.get('guide', [])
        
        # 가이드 목록
        guide_text = "\n".join([f"• {g}" for g in guides[:5]]) if guides else "N/A"
        
        fields = []
        fields.append({
            "name": "✅ 대응 가이드",
            "value": self._truncate(guide_text, 1024),
            "inline": False
        })
        
        # 영상 출처
        yt_title = report_data.get('yt_title', 'N/A')
        yt_url = report_data.get('yt_url', '')
        if yt_url and yt_url != 'N/A':
            source_text = f"[{yt_title}]({yt_url})"
        else:
            source_text = yt_title
        
        fields.append({
            "name": "📺 분석 영상",
            "value": source_text,
            "inline": False
        })
        
        embed = {
            "title": f"🏁 대응 전략: {position}",
            "color": style['color'],
            "fields": fields,
            "footer": {
                "text": f"GENSE v1.8 │ Powered by Gemini │ {report_data.get('mode', 'Standard')} Mode"
            }
        }
        
        return embed

    def send_report(self, report_data):
        """3-Embed 구조 리포트 전송"""
        if not self.webhook_url or "https" not in self.webhook_url:
            print("⚠️ Discord Webhook URL이 유효하지 않습니다.")
            return

        signal = str(report_data.get('signal', 'HOLD'))
        style = self._signal_style(signal)

        embed1 = self._build_embed_header(report_data, style)
        embed2 = self._build_embed_analysis(report_data, style)
        embed3 = self._build_embed_strategy(report_data, style)

        try:
            # 3개 Embed를 단일 메시지로 전송 (Discord는 메시지당 최대 10 Embeds 지원)
            # 다만 총 6,000자 제한이 있으므로, 초과 시 분할 전송
            all_embeds = [embed1, embed2, embed3]
            
            # 총 글자수 체크
            total_chars = self._count_embed_chars(all_embeds)
            
            if total_chars <= 6000:
                # 단일 메시지로 전송 (가장 깔끔한 UX)
                res = requests.post(self.webhook_url, json={"embeds": all_embeds}, timeout=15)
                if res.status_code != 204:
                    print(f"⚠️ Discord 단일전송 실패 ({res.status_code}), 분할 전송 시도...")
                    self._send_split_embeds(all_embeds)
            else:
                # 6,000자 초과 시 분할 전송
                print(f"📏 Embed 총 {total_chars}자 → 분할 전송")
                self._send_split_embeds(all_embeds)
            
            print("✅ Discord Report Sent Successfully (3-Embed)")
        except Exception as e:
            print(f"❌ Discord Error: {e}")

    def _send_split_embeds(self, embeds):
        """Embed를 개별 메시지로 분할 전송"""
        for embed in embeds:
            try:
                requests.post(self.webhook_url, json={"embeds": [embed]}, timeout=10)
            except Exception as e:
                print(f"⚠️ Embed 분할 전송 에러: {e}")

    def _count_embed_chars(self, embeds):
        """Discord Embed 총 글자수 계산"""
        total = 0
        for embed in embeds:
            total += len(embed.get('title', ''))
            total += len(embed.get('description', ''))
            footer = embed.get('footer', {})
            total += len(footer.get('text', ''))
            for field in embed.get('fields', []):
                total += len(field.get('name', ''))
                total += len(field.get('value', ''))
        return total
