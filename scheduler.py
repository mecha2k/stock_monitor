import time
from datetime import datetime, timezone, timedelta
from typing import Optional
import config
from stock_agent import StockAgent

# 1. 한국 표준시 (KST) 타임존 설정
KST = timezone(timedelta(hours=9))

def run_scheduler() -> None:
    """
    백그라운드에서 주기적으로 시간을 검사하며,
    config.py에 지정된 시간(KST)에 맞춰 주식 에이전트를 트리거합니다.
    """
    print("⏰ [Scheduler] 주식 모니터링 스케줄러를 구동합니다.")
    print(f"⏰ [Scheduler] 매일 오전 {config.NOTIFICATION_TIME} (KST) 에 알림이 발송됩니다.")
    
    agent = StockAgent()
    last_run_date: Optional[datetime.date] = None
    
    while True:
        try:
            # 현재 한국 표준시(KST) 구하기
            now_kst = datetime.now(KST)
            current_time_str = now_kst.strftime("%H:%M")
            current_date = now_kst.date()
            
            # 지정된 시간대에 돌입하고, 오늘 하루 동안 실행되지 않았을 경우 작동
            if current_time_str == config.NOTIFICATION_TIME and last_run_date != current_date:
                print(f"⏰ [Scheduler] 예약된 시간({config.NOTIFICATION_TIME})에 도달했습니다. 분석을 시작합니다.")
                agent.run_daily_workflow()
                last_run_date = current_date
                print(f"⏰ [Scheduler] 일일 분석이 정상적으로 마무리되었습니다. 다음 트리거를 대기합니다.")
            
            # 과도한 CPU 사용량 방지를 위해 30초 대기
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n⏰ [Scheduler] 사용자에 의해 스케줄러가 종료되었습니다.")
            break
        except Exception as e:
            print(f"⏰ [Scheduler] 루프 수행 중 에러 발생: {e}")
            time.sleep(60)  # 에러 발생 시 대기 시간 소폭 증가 후 재시도

if __name__ == "__main__":
    run_scheduler()
