import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base, SessionLocal, engine
from app.models import (
    ActionRecord,
    AnomalyEvent,
    Case,
    CauseAnalysis,
    ProcessData,
    QualityPrediction,
    RecommendedAction,
    Scenario,
    User,
    VariableThreshold,
)
from app.scenario_loader import load_scenario_csv
from app.security import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

if not db.query(User).filter(User.username == "worker1").first():
    db.add(
        User(
            username="worker1",
            password_hash=hash_password("worker1234"),
            role="worker",
            name="탁강헌",
        )
    )

if not db.query(User).filter(User.username == "manager1").first():
    db.add(
        User(
            username="manager1",
            password_hash=hash_password("manager1234"),
            role="manager",
            name="강성윤",
        )
    )

THRESHOLDS = [
    ("금형 온도", 175.0, 172.0, 178.0, True, "℃"),
    ("사출 압력", 6.9, 6.5, 7.2, True, "MPa"),
    ("수지 양", 12.5, 12.38, 12.62, True, "g"),
    ("수지 점도 (모터 부하)", 100.0, 90.0, 110.0, True, "%"),
    ("유량 (RAM 속도)", 3.0, 2.6, 3.4, True, "mm/sec"),
    ("몰딩 시간", 120.0, 115.0, 125.0, True, "sec"),
    ("냉각 속도", 12.0, 9.0, 15.0, True, "℃/min"),
    ("작업장 습도", 45.0, 30.0, 55.0, True, "% RH"),
    ("진공 시간", 4.0, 2.5, 4.0, False, "sec"),
]

for name, golden, lower, upper, check_upper, unit in THRESHOLDS:
    existing = db.query(VariableThreshold).filter(VariableThreshold.variable_name == name).first()
    if existing is None:
        db.add(
            VariableThreshold(
                variable_name=name,
                golden_value=golden,
                lower_bound=lower,
                upper_bound=upper,
                check_upper=check_upper,
                unit=unit,
            )
        )
    else:
        existing.golden_value = golden
        existing.lower_bound = lower
        existing.upper_bound = upper
        existing.check_upper = check_upper
        existing.unit = unit

CASES = [
    (
        "금형 온도", "미만",
        "금형 히터 출력 저하로 금형 온도가 기준 하한 아래로 낮아짐",
        "금형 히터 출력 저하로 인한 금형 온도 하락",
        "수지 점도 ↑ → 패키지 두께 ↑",
        ["패키지 두께 증가"],
        "히터 출력을 높이고 금형 예열 상태를 재점검",
        "금형 온도 정상 복귀, 패키지 두께 편차 해소",
        "금형 온도가 하한 아래로 떨어지면 히터 출력과 예열 상태를 우선 점검한다.",
    ),
    (
        "금형 온도", "초과",
        "패키징 공정 1호기에서 금형 히터 제어 오류로 금형 온도가 기준 상한을 초과하며 지속됨",
        "금형 히터 제어 오류로 인한 과열",
        "수지 점도 ↓ → 흐름 빨라짐 → Wire sweep 위험 ↑, 온도가 과하게 높아질 시 조기경화 위험성",
        ["Wire sweep 위험", "조기경화 위험"],
        "히터 출력을 낮추고 냉각 라인을 점검",
        "10분 내 금형 온도 정상 범위로 복귀, 불량률 영향 없음",
        "금형 온도 초과 시 히터 출력을 낮추고 냉각수 유량을 확인한다.",
    ),
    (
        "사출 압력", "미만",
        "사출 실린더 압력 설정 저하로 사출 압력이 기준 하한 아래로 낮아짐",
        "사출 실린더 압력 설정 저하 또는 노즐 막힘으로 인한 충진력 부족",
        "수지 충진력 ↓ → 미충진 및 Void 위험 ↑",
        ["미충진 위험", "Void 위험"],
        "사출 압력 설정값을 상향 조정하고 노즐 상태를 점검",
        "충진력 회복, Void 위험 해소",
        "사출 압력이 하한 아래로 떨어지면 압력 설정값과 노즐 막힘 여부를 확인한다.",
    ),
    (
        "사출 압력", "초과",
        "재료 점도 저하로 사출 압력이 기준 상한을 초과함",
        "재료 점도 저하에 따른 사출 압력 상승",
        "수지 유동력 ↑ → Wire sweep 및 Die shift 위험 ↑, 수지 누출로 단자 덮임 및 설비 파손",
        ["Wire sweep 위험", "Die shift 위험", "단자 덮임/설비 파손"],
        "사출 압력 설정값을 재조정하고 재료 점도 안정화를 확인한 뒤 정상 운전",
        "압력 변동 해소, 품질 영향 없음",
        "압력이 소폭 초과되면 재료 점도 변화를 먼저 의심하고 압력 설정값을 재조정한다.",
    ),
    (
        "수지 양", "미만",
        "수지 공급량이 기준 하한 아래로 낮아짐",
        "수지 공급 장치의 계량 오차 또는 카트리지 잔량 부족",
        "수지 부족 → 미충진, 패키지 두께 ↓",
        ["미충진 위험", "패키지 두께 감소"],
        "수지 카트리지 잔량과 계량 장치 캘리브레이션을 점검",
        "수지 공급량 정상 복귀, 미충진 위험 해소",
        "수지 양이 하한 아래로 떨어지면 카트리지 잔량과 계량 장치를 점검한다.",
    ),
    (
        "수지 양", "초과",
        "수지 공급량이 기준 상한을 초과함",
        "수지 공급 장치의 계량 오차로 인한 과다 투입",
        "수지 과다 → Flash, 패키지 두께 ↑",
        ["Flash 위험", "패키지 두께 증가"],
        "계량 장치를 재조정하고 투입량 설정값을 낮춤",
        "수지 공급량 정상화, Flash 발생 위험 해소",
        "수지 양이 상한을 초과하면 계량 장치 설정값을 낮춰 재조정한다.",
    ),
    (
        "수지 점도 (모터 부하)", "미만",
        "금형 온도 상승의 여파로 재료 점도(모터 부하)가 기준 하한 아래로 낮아짐",
        "재료 온도 상승 또는 재료 열화로 인한 점도 저하",
        "수지 유동력 ↑ → Wire sweep 위험 ↑",
        ["Wire sweep 위험"],
        "재료 온도를 안정화하고 점도 저하 원인을 점검",
        "모터 부하 정상 복귀, Wire sweep 위험 해소",
        "모터 부하가 하한 아래로 떨어지면 재료 온도와 점도 저하 원인을 점검한다.",
    ),
    (
        "수지 점도 (모터 부하)", "초과",
        "수지 점도(모터 부하)가 기준 상한을 초과함",
        "재료 냉각 과다 또는 재료 노후화로 인한 점도 상승",
        "수지 유동력 ↓ → 미충진 및 Void 위험 ↑",
        ["미충진 위험", "Void 위험"],
        "재료 온도를 높이고 재료 상태를 점검",
        "모터 부하 정상 복귀, 미충진 위험 해소",
        "모터 부하가 상한을 초과하면 재료 온도와 재료 상태를 점검한다.",
    ),
    (
        "유량 (RAM 속도)", "미만",
        "RAM 속도가 기준 하한 아래로 낮아짐",
        "사출 구동부 압력 저하 또는 밸브 응답 지연",
        "충진 시간 ↑ → 공정 시간 증가 및 경화 전 충진 실패 가능성 ↑",
        ["충진 실패 위험"],
        "구동부 압력과 밸브 응답 상태를 점검",
        "RAM 속도 정상 복귀, 충진 시간 안정화",
        "RAM 속도가 하한 아래로 떨어지면 구동부 압력과 밸브 응답을 점검한다.",
    ),
    (
        "유량 (RAM 속도)", "초과",
        "RAM 속도가 기준 상한을 초과함",
        "사출 구동부 설정값 오류로 인한 과속",
        "유동 속도 ↑ → Wire sweep 및 Void 위험 ↑",
        ["Wire sweep 위험", "Void 위험"],
        "RAM 속도 설정값을 낮추고 구동부를 재점검",
        "RAM 속도 정상 복귀, Wire sweep 위험 해소",
        "RAM 속도가 상한을 초과하면 구동부 설정값을 낮춰 재조정한다.",
    ),
    (
        "몰딩 시간", "미만",
        "경화 타이머 설정 오류로 몰딩 시간이 기준 하한 아래로 짧아짐",
        "경화 타이머 설정 오류 또는 공정 조기 종료",
        "경화 부족 → 강도/신뢰성 ↓, 패키지 찢어짐이나 Crack 발생 위험 ↑",
        ["강도/신뢰성 저하", "Crack 위험"],
        "경화 타이머 설정값을 재확인하고 정상값으로 복원",
        "몰딩 시간 정상 복귀, 경화 부족 위험 해소",
        "몰딩 시간이 하한 아래로 짧아지면 경화 타이머 설정을 재확인한다.",
    ),
    (
        "몰딩 시간", "초과",
        "몰딩 시간이 기준 상한을 초과함",
        "경화 타이머 설정 오류로 인한 과도한 경화 시간",
        "생산 시간 증가 및 과도한 경화 및 열 이력 → 수축 및 Warpage 위험 ↑",
        ["Warpage 위험"],
        "경화 타이머 설정값을 낮추고 설비 동작을 점검",
        "몰딩 시간 정상 복귀, Warpage 위험 해소",
        "몰딩 시간이 상한을 초과하면 경화 타이머 설정을 낮춰 재조정한다.",
    ),
    (
        "냉각 속도", "미만",
        "냉각수 유량 저하로 냉각 속도가 기준 하한 아래로 낮아짐",
        "냉각수 유량 저하 또는 냉각 라인 막힘",
        "냉각 속도 ↓ → 수축 진행 시간 및 작업 시간 ↑",
        ["작업 시간 지연"],
        "냉각수 유량과 냉각 라인 상태를 점검",
        "냉각 속도 정상 복귀, 작업 시간 지연 해소",
        "냉각 속도가 하한 아래로 떨어지면 냉각수 유량과 라인 막힘 여부를 점검한다.",
    ),
    (
        "냉각 속도", "초과",
        "냉각 속도가 기준 상한을 초과함",
        "냉각수 유량 과다 또는 냉각 설정값 오류",
        "냉각 속도 ↑ → 열응력 및 Warpage, Crack 위험 ↑",
        ["Warpage 위험", "Crack 위험"],
        "냉각수 유량을 낮추고 냉각 설정값을 재조정",
        "냉각 속도 정상 복귀, Warpage 위험 해소",
        "냉각 속도가 상한을 초과하면 냉각수 유량을 낮춰 재조정한다.",
    ),
    (
        "작업장 습도", "미만",
        "작업장 습도가 기준 하한 아래로 낮아짐",
        "공조 설비 가습 기능 저하 또는 외기 유입",
        "정전기 발생률 ↑ → ESD 위험 ↑",
        ["ESD 위험"],
        "가습 설비를 가동하고 작업장 밀폐 상태를 점검",
        "습도 정상 복귀, ESD 위험 해소",
        "습도가 하한 아래로 떨어지면 가습 설비와 밀폐 상태를 점검한다.",
    ),
    (
        "작업장 습도", "초과",
        "작업장 습도가 기준 상한을 초과함",
        "공조 설비 제습 기능 저하",
        "패키지가 수분 흡수 → 박리, Crack 위험 ↑",
        ["박리 위험", "Crack 위험"],
        "제습 설비를 가동하고 공조 필터를 점검",
        "습도 정상 복귀, 박리 위험 해소",
        "습도가 상한을 초과하면 제습 설비와 공조 필터를 점검한다.",
    ),
    (
        "진공 시간", "미만",
        "진공 펌프 성능 저하로 진공 시간이 기준 하한 아래로 짧아짐",
        "진공 펌프 성능 저하 또는 진공 타이머 설정 오류",
        "공기 제거 부족, Void 위험 ↑",
        ["Void 위험"],
        "진공 펌프 상태를 점검하고 타이머 설정값을 복원",
        "진공 시간 정상 복귀, Void 위험 해소",
        "진공 시간이 하한 아래로 짧아지면 진공 펌프와 타이머 설정을 점검한다.",
    ),
]

for category, direction, situation, cause, quality_impact, defect_tags, response, result, manual_text in CASES:
    existing = db.query(Case).filter(Case.category == category, Case.direction == direction).first()
    if existing is None:
        db.add(
            Case(
                category=category,
                direction=direction,
                situation=situation,
                cause=cause,
                quality_impact=quality_impact,
                defect_tags=defect_tags,
                response=response,
                result=result,
                manual_text=manual_text,
            )
        )
    else:
        existing.situation = situation
        existing.cause = cause
        existing.quality_impact = quality_impact
        existing.defect_tags = defect_tags
        existing.response = response
        existing.result = result
        existing.manual_text = manual_text

db.commit()

existing_scenario = db.query(Scenario).filter(Scenario.name == "샘플 시나리오").first()
if existing_scenario is not None:
    event_ids = [
        e.id for e in db.query(AnomalyEvent).filter(AnomalyEvent.scenario_id == existing_scenario.id).all()
    ]
    if event_ids:
        db.query(ActionRecord).filter(ActionRecord.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(RecommendedAction).filter(RecommendedAction.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(QualityPrediction).filter(QualityPrediction.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(CauseAnalysis).filter(CauseAnalysis.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
    db.query(AnomalyEvent).filter(AnomalyEvent.scenario_id == existing_scenario.id).delete()
    db.query(ProcessData).filter(ProcessData.scenario_id == existing_scenario.id).delete()
    db.delete(existing_scenario)
    db.commit()

sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_scenario.csv")
load_scenario_csv(db, "샘플 시나리오", os.path.abspath(sample_path))

db.close()

print("시드 완료")
