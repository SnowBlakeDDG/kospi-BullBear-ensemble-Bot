import requests
from datetime import datetime

class DiscordNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_report(self, report_data):
        if not self.webhook_url or "https" not in self.webhook_url:
            return

        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        signal = str(report_data.get('signal', 'HOLD'))
        emoji = "🚀" if signal == "BUY" else "🆘" if signal == "SELL" else "⚖️"
        
        # 지표별 상세 표 (Markdown Table)
        details = report_data['details']
        table = [
            "| 지표 | 방향(Bull/Bear) | 강도(Str) | 가중치 적용값 |",
            "| :--- | :---: | :---: | :---: |",
            f"| 유튜브 | {details['youtube']['dir']} | {details['youtube']['str']} | {details['youtube']['val']:.4f} |",
            f"| KORU | {details['koru']['dir']} | {details['koru']['str']} | {details['koru']['val']:.4f} |",
            f"| 수급 | {details['supply_demand']['dir']} | {details['supply_demand']['str']} | {details['supply_demand']['val']:.4f} |",
            f"| 환율 | {details['fx']['dir']} | {details['fx']['str']} | {details['fx']['val']:.4f} |"
        ]
        
        table_str = "\n".join(table)
        yt_reason = str(report_data.get('yt_reason', 'N/A'))

        header = f"""
### {emoji} G-ensemble KOSPI 분석 리포트
- **분석 일시:** {now}
- **추천 신호:** **{signal}**
- **최종 스코어:** `{report_data.get('final_score', 0)}`
- **KORU 상태:** {details['koru'].get('status', 'OK')}

**[지표별 상세 지표]**
{table_str}
        """
        
        # 분석 요약 분할 (1500자 단위)
        full_content = f"**[분석 요약 및 논거]**\n{yt_reason}"
        chunks = [full_content[i:i+1500] for i in range(0, len(full_content), 1500)]

        try:
            requests.post(self.webhook_url, json={"content": header.strip()}, timeout=10)
            for i, chunk in enumerate(chunks):
                msg = f"(파트 {i+1}/{len(chunks)})\n{chunk}" if len(chunks) > 1 else chunk
                requests.post(self.webhook_url, json={"content": msg}, timeout=10)
            print("✅ Discord Report Sent Successfully")
        except Exception as e:
            print(f"❌ Discord Error: {e}")
