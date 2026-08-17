import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-flash-lite-latest"

_api_key = os.getenv("GEMINI_API_KEY")
_client = genai.Client(api_key=_api_key) if _api_key else None


def generate_holistic_causes(contributing: list[dict]):
    if _client is None:
        return None

    variable_lines = []
    for v in contributing:
        case = v["case"]
        if case is not None:
            causes_text = " / ".join(f"{c['name']}({c['mechanism']})" for c in case.possible_causes)
            case_context = f"유사 사례 - 상황: {case.situation} / 알려진 원인 후보: {causes_text} / 결과: {case.result}"
        else:
            case_context = "일치하는 과거 사례 없음"
        variable_lines.append(
            f"- {v['variable_name']}: 기준값 대비 {v['direction']}, 기여도 {v['contribution_pct']:.1f}%, 현재값 {v['current_value']}. {case_context}"
        )

    prompt = (
        "다음은 제조 공정에서 동시에 발생한 이상 변수 목록이야.\n\n"
        + "\n".join(variable_lines)
        + "\n\n1단계: 먼저 가능한 모든 원인 후보를 폭넓게 생각해봐. 각 변수에 달린 \"알려진 원인 후보\"는 과거 숙련자들이 실제로 확인했던 원인이니 "
        "개별 원인 후보를 만들 때 우선적으로 참고하고, 필요하면 거기서 더 구체화하거나 새로운 후보를 추가해도 돼. 두 종류를 모두 고려해야 해 — "
        "(a) 변수 하나만으로 설명되는 개별 원인 후보(같은 변수라도 서로 다른 기계적 원인이 가능하면 각각 별도 후보로), "
        "(b) 여러 변수가 하나의 근본 원인으로 설명될 수 있는 결합 원인 후보. "
        "결합 원인 후보는 다음 둘 중 하나의 명확한 근거가 있을 때만 만들어: "
        "① 매칭된 유사 사례 문구에 이미 그 변수들 사이의 인과관계나 연쇄 반응이 언급되어 있거나, "
        "② 같은 물리적 설비/공정 구간에 속해 있어 한쪽의 기계적 결함이 다른 쪽에 영향을 준다는 것이 상식적으로 명백한 경우. "
        "단지 같은 시점에 함께 이상이 발생했다는 사실만으로는 결합 원인을 만들면 안 돼 — "
        "그런 경우엔 각 변수를 개별 원인으로 나눠서 후보에 올려. "
        "결합 원인 후보가 하나도 없어도 전혀 문제 없어 — 근거 없이 억지로 묶는 것보다 개별 원인 3개를 내놓는 게 훨씬 낫다.\n\n"
        "2단계: 이 모든 후보 중에서 실제로 가장 그럴듯한 순서로 정확히 3개를 골라 순위를 매겨. "
        "변수가 하나뿐이면 그 변수에 대한 서로 다른 원인 후보 3개가 될 수 있고, 변수가 여럿이고 서로 무관하면 각각의 개별 원인이 상위에 올 수 있고, "
        "실제로 연관되어 있다면 결합 원인이 1순위가 될 수도 있어 — 정답을 미리 정해두지 말고 후보들을 비교해서 진짜 순위를 매겨.\n\n"
        "중요한 제약: 각 원인은 반드시 작업자가 실제로 점검하거나 조치할 수 있는 설비적·기계적 결함(예: 히터 제어 오류, 센서 이상, 밸브 고장, 원료 계량 오차 등)이어야 해. "
        "다른 변수의 수치 변화 자체를 원인으로 제시하면 안 돼. "
        '예를 들어 "재료 점도 저하에 따른 사출 압력 상승"처럼 한 변수의 변화가 다른 변수를 유발했다는 식의 설명은 금지야. '
        '대신 "히터 온도 제어 이상으로 인한 재료 점도 저하 및 사출 압력 상승"처럼, 그 변수 변화들을 유발한 근본적인 설비/공정상의 결함을 원인으로 제시해.\n\n'
        "각 원인마다 그 원인일 가능성(likelihood_pct, 0~100 사이 숫자)을 실제 후보 간 비교를 근거로 직접 판단해서 매겨줘. "
        "1순위 > 2순위 > 3순위 순으로 감소해야 하고, 후보들의 그럴듯함 차이가 크면 숫자 차이도 크게, 비슷하면 차이도 작게 반영해.\n\n"
        "related_variables가 2개 이상인 결합 원인에는 반드시 link_justification 필드에 위 ①·② 중 어느 근거인지와 구체적 이유를 적어. "
        "근거를 못 대겠으면 애초에 결합 원인으로 만들지 말고 개별 원인으로 나눠. 변수가 1개뿐인 원인은 link_justification을 빈 문자열로 둬.\n\n"
        "description은 두 부분을 모두 포함해서 3~4문장으로 풍부하게 써: "
        "(1) 결함이 발생한 지점부터 관측된 변수 이상까지 이어지는 물리적 메커니즘을 \"결함 발생 → 중간 물리적 변화(온도/압력/점도 등 실제 값의 변화 방향과 정도) → 최종적으로 관측된 변수 이상\" 순서로 단계별로 구체적으로 서술하고, "
        "(2) 위에 주어진 유사 사례가 있다면 그 사례의 상황(situation)과 결과(result)를 구체적으로 인용해서, "
        "\"과거 유사 사례(그 상황 내용)에서도 같은 패턴이 있었고, 그때는 (그 결과 내용)로 이어졌다\"는 식으로 이번 판단이 과거 숙련자들의 경험적 사례에 근거하고 있음을 자연스럽게 드러내. "
        "유사 사례가 없는 변수라면 (2)는 생략하고 (1)만 상세히 써도 돼. "
        "단순히 \"~로 인해 ~이 발생했다\"는 한 문장 요약이 아니라, 중간 과정과 사례 근거를 눈에 보이듯 풀어써야 해.\n\n"
        "다음 JSON 형식으로만 응답해: "
        '{"causes": [{"cause_name": "설비/공정상의 결함을 요약한 짧은 명사구", "description": "물리적 메커니즘 + 유사 사례 근거를 포함한 3~4문장", "related_variables": ["관련된 변수명"], "link_justification": "", "likelihood_pct": 0}]}\n'
        "related_variables는 반드시 위 목록에 나열된 변수명 중에서만 골라야 하고, 각 원인마다 최소 1개는 있어야 해."
    )

    try:
        response = _client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        data = json.loads(response.text)
        causes = data.get("causes")
        if not causes or not isinstance(causes, list):
            return None
        return causes
    except Exception:
        return None
