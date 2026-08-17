import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base, SessionLocal, engine
from app.models import (
    ActionRecord,
    AnomalyEvent,
    Case,
    CauseSummary,
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
        [
            {"name": "금형 히터 출력 저하", "mechanism": "히터 소자 노후화 또는 전력 공급 불안정으로 목표 온도까지 가열이 되지 않음"},
            {"name": "금형 예열 시간 부족", "mechanism": "가동 초기 예열 사이클이 충분히 진행되지 않아 금형 자체 온도가 목표치에 도달하지 못함"},
            {"name": "온도 센서 접촉 불량", "mechanism": "열전대 접촉 불량으로 실제보다 낮은 온도가 측정되어 제어기가 필요 이상으로 낮은 출력을 유지"},
        ],
        "수지 점도 ↑ → 패키지 두께 ↑",
        ["패키지 두께 증가"],
        "히터 출력을 높이고 금형 예열 상태를 재점검",
        "금형 온도 정상 복귀, 패키지 두께 편차 해소",
        "금형 온도가 하한 아래로 떨어지면 히터 출력과 예열 상태를 우선 점검한다.",
    ),
    (
        "금형 온도", "초과",
        "패키징 공정 1호기에서 금형 히터 제어 오류로 금형 온도가 기준 상한을 초과하며 지속됨",
        [
            {"name": "금형 히터 제어기(PID) 오작동", "mechanism": "온도 제어 로직 오류로 히터가 목표치 도달 후에도 출력을 낮추지 않고 계속 가열"},
            {"name": "냉각수 유량 저하", "mechanism": "냉각 라인 스케일 축적이나 밸브 고착으로 금형에서 열을 충분히 빼가지 못해 온도가 누적 상승"},
            {"name": "히터 릴레이(SSR) 고장", "mechanism": "솔리드 스테이트 릴레이가 On 상태로 고착되어 히터가 상시 최대 출력으로 작동"},
        ],
        "수지 점도 ↓ → 흐름 빨라짐 → Wire sweep 위험 ↑, 온도가 과하게 높아질 시 조기경화 위험성",
        ["Wire sweep 위험", "조기경화 위험"],
        "히터 출력을 낮추고 냉각 라인을 점검",
        "10분 내 금형 온도 정상 범위로 복귀, 불량률 영향 없음",
        "금형 온도 초과 시 히터 출력을 낮추고 냉각수 유량을 확인한다.",
    ),
    (
        "사출 압력", "미만",
        "사출 실린더 압력 설정 저하로 사출 압력이 기준 하한 아래로 낮아짐",
        [
            {"name": "사출 실린더 압력 설정 저하", "mechanism": "유압 펌프 압력 설정값이 낮게 조정되어 사출 시 충분한 압력이 전달되지 않음"},
            {"name": "노즐 막힘", "mechanism": "노즐 내부에 경화된 수지 잔여물이 쌓여 유로가 좁아지면서 압력 전달이 저하됨"},
            {"name": "유압 실린더 씰 마모", "mechanism": "실린더 내부 씰이 마모되어 유압이 새면서 실제 사출 압력이 설정값보다 낮게 형성됨"},
        ],
        "수지 충진력 ↓ → 미충진 및 Void 위험 ↑",
        ["미충진 위험", "Void 위험"],
        "사출 압력 설정값을 상향 조정하고 노즐 상태를 점검",
        "충진력 회복, Void 위험 해소",
        "사출 압력이 하한 아래로 떨어지면 압력 설정값과 노즐 막힘 여부를 확인한다.",
    ),
    (
        "사출 압력", "초과",
        "재료 점도 저하로 사출 압력이 기준 상한을 초과함",
        [
            {"name": "사출 압력 릴리프 밸브 응답 지연", "mechanism": "릴리프 밸브 내 이물질 또는 스프링 피로로 과압 발생 시 즉시 배출되지 않아 압력이 기준치 이상으로 상승"},
            {"name": "노즐/러너 부분 막힘에 따른 배압 상승", "mechanism": "유로 단면적이 줄어들면서 동일 유량을 밀어내기 위해 필요한 압력이 상승"},
            {"name": "사출 속도(RAM) 설정 과다", "mechanism": "RAM 속도가 과도하게 높게 설정되어 짧은 시간에 많은 양을 밀어내려다 압력이 급상승"},
        ],
        "수지 유동력 ↑ → Wire sweep 및 Die shift 위험 ↑, 수지 누출로 단자 덮임 및 설비 파손",
        ["Wire sweep 위험", "Die shift 위험", "단자 덮임/설비 파손"],
        "사출 압력 설정값을 재조정하고 재료 점도 안정화를 확인한 뒤 정상 운전",
        "압력 변동 해소, 품질 영향 없음",
        "압력이 소폭 초과되면 재료 점도 변화를 먼저 의심하고 압력 설정값을 재조정한다.",
    ),
    (
        "수지 양", "미만",
        "수지 공급량이 기준 하한 아래로 낮아짐",
        [
            {"name": "수지 계량 장치 캘리브레이션 오차", "mechanism": "로드셀 또는 스크류 계량 센서의 영점 오차로 실제보다 적은 양을 투입한 것으로 판단해 공급량을 줄임"},
            {"name": "카트리지 잔량 부족", "mechanism": "원료 카트리지 내 수지가 소진되어 가는 시점에 공급 압력이 떨어지며 계량 오차가 커짐"},
            {"name": "이송 스크류 마모", "mechanism": "이송 스크류 날 마모로 동일 회전수 대비 이송되는 수지량이 줄어듦"},
        ],
        "수지 부족 → 미충진, 패키지 두께 ↓",
        ["미충진 위험", "패키지 두께 감소"],
        "수지 카트리지 잔량과 계량 장치 캘리브레이션을 점검",
        "수지 공급량 정상 복귀, 미충진 위험 해소",
        "수지 양이 하한 아래로 떨어지면 카트리지 잔량과 계량 장치를 점검한다.",
    ),
    (
        "수지 양", "초과",
        "수지 공급량이 기준 상한을 초과함",
        [
            {"name": "계량 밸브 고착", "mechanism": "계량 밸브가 완전히 닫히지 않아 설정량 이상으로 수지가 추가 유입됨"},
            {"name": "로드셀 드리프트", "mechanism": "계량 센서 값이 시간에 따라 틀어져 실제보다 적게 투입된 것으로 오판, 과다 보충 투입"},
        ],
        "수지 과다 → Flash, 패키지 두께 ↑",
        ["Flash 위험", "패키지 두께 증가"],
        "계량 장치를 재조정하고 투입량 설정값을 낮춤",
        "수지 공급량 정상화, Flash 발생 위험 해소",
        "수지 양이 상한을 초과하면 계량 장치 설정값을 낮춰 재조정한다.",
    ),
    (
        "수지 점도 (모터 부하)", "미만",
        "금형 온도 상승의 여파로 재료 점도(모터 부하)가 기준 하한 아래로 낮아짐",
        [
            {"name": "재료 히터 과열", "mechanism": "호퍼 또는 배럴 히터 과열로 수지 온도가 지나치게 올라가 점도가 낮아지고 모터 부하가 감소"},
            {"name": "원료 장시간 체류에 따른 열화", "mechanism": "원료가 배럴 내 과도하게 오래 체류하며 열화되어 유동성이 비정상적으로 높아짐"},
        ],
        "수지 유동력 ↑ → Wire sweep 위험 ↑",
        ["Wire sweep 위험"],
        "재료 온도를 안정화하고 점도 저하 원인을 점검",
        "모터 부하 정상 복귀, Wire sweep 위험 해소",
        "모터 부하가 하한 아래로 떨어지면 재료 온도와 점도 저하 원인을 점검한다.",
    ),
    (
        "수지 점도 (모터 부하)", "초과",
        "수지 점도(모터 부하)가 기준 상한을 초과함",
        [
            {"name": "재료 냉각 과다", "mechanism": "호퍼 냉각 설비 과다 작동으로 원료 온도가 지나치게 낮아져 점도가 상승, 모터 부하 증가"},
            {"name": "원료 수분 흡습에 따른 노후화", "mechanism": "원료 보관 상태 불량으로 수분을 흡수해 점도가 비정상적으로 높아짐"},
            {"name": "스크류/배럴 마모에 따른 마찰 저항 증가", "mechanism": "장비 마모로 이송 저항이 커지면서 정상 재료라도 모터 부하가 높게 측정됨"},
        ],
        "수지 유동력 ↓ → 미충진 및 Void 위험 ↑",
        ["미충진 위험", "Void 위험"],
        "재료 온도를 높이고 재료 상태를 점검",
        "모터 부하 정상 복귀, 미충진 위험 해소",
        "모터 부하가 상한을 초과하면 재료 온도와 재료 상태를 점검한다.",
    ),
    (
        "유량 (RAM 속도)", "미만",
        "RAM 속도가 기준 하한 아래로 낮아짐",
        [
            {"name": "사출 구동부(유압/서보) 압력 저하", "mechanism": "구동 유닛의 출력 저하로 RAM이 목표 속도로 가속하지 못함"},
            {"name": "밸브 응답 지연", "mechanism": "서보밸브 또는 유량 제어 밸브의 기계적 마모로 명령 대비 실제 반응 속도가 느려짐"},
        ],
        "충진 시간 ↑ → 공정 시간 증가 및 경화 전 충진 실패 가능성 ↑",
        ["충진 실패 위험"],
        "구동부 압력과 밸브 응답 상태를 점검",
        "RAM 속도 정상 복귀, 충진 시간 안정화",
        "RAM 속도가 하한 아래로 떨어지면 구동부 압력과 밸브 응답을 점검한다.",
    ),
    (
        "유량 (RAM 속도)", "초과",
        "RAM 속도가 기준 상한을 초과함",
        [
            {"name": "사출 구동부 설정값 오류", "mechanism": "속도 프로파일 파라미터가 잘못 입력되어 목표 속도 이상으로 RAM이 가속됨"},
            {"name": "서보밸브 오버슈트", "mechanism": "밸브 제어 게인이 과도하게 설정되어 목표치를 넘어서는 오버슈트가 발생"},
        ],
        "유동 속도 ↑ → Wire sweep 및 Void 위험 ↑",
        ["Wire sweep 위험", "Void 위험"],
        "RAM 속도 설정값을 낮추고 구동부를 재점검",
        "RAM 속도 정상 복귀, Wire sweep 위험 해소",
        "RAM 속도가 상한을 초과하면 구동부 설정값을 낮춰 재조정한다.",
    ),
    (
        "몰딩 시간", "미만",
        "경화 타이머 설정 오류로 몰딩 시간이 기준 하한 아래로 짧아짐",
        [
            {"name": "경화 타이머 설정 오류", "mechanism": "타이머 파라미터가 잘못 입력되어 규정된 경화 시간보다 일찍 공정이 종료됨"},
            {"name": "공정 인터록 오작동", "mechanism": "센서 오신호로 공정 완료 조건이 실제보다 일찍 충족된 것으로 판단해 조기 종료됨"},
        ],
        "경화 부족 → 강도/신뢰성 ↓, 패키지 찢어짐이나 Crack 발생 위험 ↑",
        ["강도/신뢰성 저하", "Crack 위험"],
        "경화 타이머 설정값을 재확인하고 정상값으로 복원",
        "몰딩 시간 정상 복귀, 경화 부족 위험 해소",
        "몰딩 시간이 하한 아래로 짧아지면 경화 타이머 설정을 재확인한다.",
    ),
    (
        "몰딩 시간", "초과",
        "몰딩 시간이 기준 상한을 초과함",
        [
            {"name": "경화 타이머 설정 오류", "mechanism": "타이머 파라미터가 과도하게 길게 입력되어 필요 이상으로 공정이 지속됨"},
            {"name": "온도 센서 이상에 따른 경화 완료 판정 지연", "mechanism": "온도 센서가 실제 경화 완료 시점보다 늦게 도달 신호를 보내 공정 종료가 지연됨"},
        ],
        "생산 시간 증가 및 과도한 경화 및 열 이력 → 수축 및 Warpage 위험 ↑",
        ["Warpage 위험"],
        "경화 타이머 설정값을 낮추고 설비 동작을 점검",
        "몰딩 시간 정상 복귀, Warpage 위험 해소",
        "몰딩 시간이 상한을 초과하면 경화 타이머 설정을 낮춰 재조정한다.",
    ),
    (
        "냉각 속도", "미만",
        "냉각수 유량 저하로 냉각 속도가 기준 하한 아래로 낮아짐",
        [
            {"name": "냉각수 유량 저하", "mechanism": "냉각 라인 스케일 축적이나 펌프 성능 저하로 냉각수 순환량이 줄어 냉각이 느려짐"},
            {"name": "냉각 라인 막힘", "mechanism": "이물질이나 스케일로 냉각수 유로가 부분적으로 막혀 열교환 효율이 떨어짐"},
        ],
        "냉각 속도 ↓ → 수축 진행 시간 및 작업 시간 ↑",
        ["작업 시간 지연"],
        "냉각수 유량과 냉각 라인 상태를 점검",
        "냉각 속도 정상 복귀, 작업 시간 지연 해소",
        "냉각 속도가 하한 아래로 떨어지면 냉각수 유량과 라인 막힘 여부를 점검한다.",
    ),
    (
        "냉각 속도", "초과",
        "냉각 속도가 기준 상한을 초과함",
        [
            {"name": "냉각수 유량 과다", "mechanism": "냉각 펌프 출력이 과도하게 설정되어 필요 이상으로 빠르게 열을 빼앗음"},
            {"name": "냉각 설정값 오류", "mechanism": "냉각 프로파일 파라미터가 잘못 입력되어 목표보다 빠른 냉각 속도로 제어됨"},
        ],
        "냉각 속도 ↑ → 열응력 및 Warpage, Crack 위험 ↑",
        ["Warpage 위험", "Crack 위험"],
        "냉각수 유량을 낮추고 냉각 설정값을 재조정",
        "냉각 속도 정상 복귀, Warpage 위험 해소",
        "냉각 속도가 상한을 초과하면 냉각수 유량을 낮춰 재조정한다.",
    ),
    (
        "작업장 습도", "미만",
        "작업장 습도가 기준 하한 아래로 낮아짐",
        [
            {"name": "공조 설비 가습 기능 저하", "mechanism": "가습기 급수 부족 또는 필터 막힘으로 목표 습도까지 가습이 이루어지지 않음"},
            {"name": "외기 유입", "mechanism": "출입문/창호 밀폐 불량으로 건조한 외기가 유입되어 실내 습도가 낮아짐"},
        ],
        "정전기 발생률 ↑ → ESD 위험 ↑",
        ["ESD 위험"],
        "가습 설비를 가동하고 작업장 밀폐 상태를 점검",
        "습도 정상 복귀, ESD 위험 해소",
        "습도가 하한 아래로 떨어지면 가습 설비와 밀폐 상태를 점검한다.",
    ),
    (
        "작업장 습도", "초과",
        "작업장 습도가 기준 상한을 초과함",
        [
            {"name": "공조 설비 제습 기능 저하", "mechanism": "제습기 냉매 부족 또는 필터 오염으로 제습 성능이 떨어져 습도가 상승"},
            {"name": "외기 고습 공기 유입", "mechanism": "장마철 등 외부 고습 공기가 밀폐 불량 지점을 통해 유입됨"},
        ],
        "패키지가 수분 흡수 → 박리, Crack 위험 ↑",
        ["박리 위험", "Crack 위험"],
        "제습 설비를 가동하고 공조 필터를 점검",
        "습도 정상 복귀, 박리 위험 해소",
        "습도가 상한을 초과하면 제습 설비와 공조 필터를 점검한다.",
    ),
    (
        "진공 시간", "미만",
        "진공 펌프 성능 저하로 진공 시간이 기준 하한 아래로 짧아짐",
        [
            {"name": "진공 펌프 성능 저하", "mechanism": "펌프 오일 오염 또는 로터 마모로 배기 유량이 줄어 목표 진공도 도달까지 시간이 오래 걸림"},
            {"name": "진공 타이머 설정 오류", "mechanism": "타이머 파라미터가 짧게 설정되어 목표 진공도 도달 전에 공정이 종료됨"},
            {"name": "챔버 씰링 불량(미세 누기)", "mechanism": "도어 가스켓 노후화로 외부 공기가 미세하게 유입되어 목표 진공도 도달이 어려움"},
        ],
        "공기 제거 부족, Void 위험 ↑",
        ["Void 위험"],
        "진공 펌프 상태를 점검하고 타이머 설정값을 복원",
        "진공 시간 정상 복귀, Void 위험 해소",
        "진공 시간이 하한 아래로 짧아지면 진공 펌프와 타이머 설정을 점검한다.",
    ),
]

for category, direction, situation, possible_causes, quality_impact, defect_tags, response, result, manual_text in CASES:
    existing = db.query(Case).filter(Case.category == category, Case.direction == direction).first()
    if existing is None:
        db.add(
            Case(
                category=category,
                direction=direction,
                situation=situation,
                possible_causes=possible_causes,
                quality_impact=quality_impact,
                defect_tags=defect_tags,
                response=response,
                result=result,
                manual_text=manual_text,
            )
        )
    else:
        existing.situation = situation
        existing.possible_causes = possible_causes
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
        db.query(CauseSummary).filter(CauseSummary.anomaly_event_id.in_(event_ids)).delete(synchronize_session=False)
    db.query(AnomalyEvent).filter(AnomalyEvent.scenario_id == existing_scenario.id).delete()
    db.query(ProcessData).filter(ProcessData.scenario_id == existing_scenario.id).delete()
    db.delete(existing_scenario)
    db.commit()

sample_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample_scenario.csv")
load_scenario_csv(db, "샘플 시나리오", os.path.abspath(sample_path))

db.close()

print("시드 완료")
