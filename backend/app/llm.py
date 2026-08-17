import json
import os
import sys
import traceback

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-flash-lite-latest"

_api_key = os.getenv("GEMINI_API_KEY")
_client = genai.Client(api_key=_api_key) if _api_key else None


def _request_items(prompt: str, key: str):
    try:
        response = _client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        data = json.loads(response.text, strict=False)
        items = data if isinstance(data, list) else data.get(key)
        if not items or not isinstance(items, list):
            print(f"[llm] {key}: unexpected response shape {type(data).__name__}", file=sys.stderr)
            return None
        print(f"[llm] {key}: {len(items)} items", file=sys.stderr)
        return items
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return None


def generate_holistic_causes(contributing: list[dict]):
    if _client is None:
        return None

    variable_lines = []
    for v in contributing:
        case = v["case"]
        if case is not None:
            causes_text = " / ".join(f"{c['name']}({c['mechanism']})" for c in case.possible_causes)
            results_text = " / ".join(r["result"] for r in case.responses)
            case_context = f"유사 사례 - 상황: {case.situation} / 알려진 원인 후보: {causes_text} / 조치 결과: {results_text}"
        else:
            case_context = "일치하는 과거 사례 없음"
        variable_lines.append(
            f"- {v['variable_name']}: 기준값 대비 {v['direction']}, 기여도 {v['contribution_pct']:.1f}%. {case_context}"
        )

    prompt = (
        "다음은 제조 공정에서 동시에 발생한 이상 변수 목록이야.\n\n"
        + "\n".join(variable_lines)
        + "\n\n글쓰기 규칙(가장 중요, 다른 모든 지시보다 우선): 너는 지금부터 cause_name과 description을 쓸 때, "
        "현재 이상 건의 결함·메커니즘을 설명하는 모든 문장을 반드시 \"~것으로 추정됩니다\" 또는 \"~일 가능성이 있습니다\"로 끝내야 해. "
        "\"~된다\", \"~한다\", \"~했다\", \"~되었다\", \"~이다\"로 끝나는 문장은 한 번이라도 쓰면 안 돼. "
        "예: (금지) \"온도가 200까지 상승한다\" → (허용) \"온도가 200까지 상승한 것으로 추정됩니다\". "
        "과거 사례의 결과를 인용하는 부분(예: 그때는 ~로 이어졌다)만 예외로 단정형을 써도 돼.\n\n"
        "1단계: 먼저 가능한 모든 원인 후보를 폭넓게 생각해봐. 각 변수에 달린 \"알려진 원인 후보\"는 과거 숙련자들이 실제로 확인했던 원인이니 "
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
        "매우 중요한 제약: cause_name과 description 어디에도 현재값 같은 구체적인 숫자(예: 200.0, 78, 7.8)를 절대 인용하지 마. "
        "이 수치는 화면의 다른 표에 이미 표시되고 있고, 여기서 숫자를 인용하면 나중에 값이 갱신돼도 이 설명은 갱신되지 않아 틀린 숫자로 남게 돼. "
        "대신 \"크게 상승\", \"기준 상한을 초과\", \"소폭 저하\"처럼 방향과 정도를 정성적으로만 표현해.\n\n"
        "description은 두 부분을 모두 포함해서 3~4문장으로 풍부하게 써: "
        "(1) 결함이 발생한 지점부터 관측된 변수 이상까지 이어지는 물리적 메커니즘을 \"결함 발생 → 중간 물리적 변화(온도/압력/점도 등의 변화 방향과 정도를 정성적으로) → 최종적으로 관측된 변수 이상\" 순서로 단계별로 구체적으로 서술하고, "
        "(2) 위에 주어진 유사 사례가 있다면 그 사례의 상황(situation)과 결과(result)를 구체적으로 인용해서, "
        "\"과거 유사 사례(그 상황 내용)에서도 같은 패턴이 있었고, 그때는 (그 결과 내용)로 이어졌다\"는 식으로 이번 판단이 과거 숙련자들의 경험적 사례에 근거하고 있음을 자연스럽게 드러내. "
        "유사 사례가 없는 변수라면 (2)는 생략하고 (1)만 상세히 써도 돼. "
        "단순히 \"~로 인해 ~이 발생했다\"는 한 문장 요약이 아니라, 중간 과정과 사례 근거를 눈에 보이듯 풀어써야 해.\n\n"
        "description은 두 단계로 작성해서 두 필드에 나눠 담아:\n"
        "1) description_draft: 위 내용을 자유롭게 3~4문장으로 작성해.\n"
        "2) description: description_draft와 내용·순서·정보는 완전히 동일하게 유지한 채, "
        "결함·메커니즘을 서술하는 문장(현재 이 이상 건에서 무슨 일이 일어났는지 설명하는 부분)만 확정 어조에서 추정 어조로 자연스럽게 고쳐 써. "
        "추정 어조 표현은 아주 다양해 — 예: \"~것으로 추정됩니다\", \"~것으로 분석됩니다\", \"~것으로 보입니다\", \"~인 것으로 판단됩니다\", "
        "\"~였을 가능성이 있습니다\", \"~일 수 있습니다\", \"~로 짐작됩니다\", \"~한 정황이 있습니다\", 문장 중간에 \"~인 듯\", \"~로 보이며\" 등을 넣어 다음 문장과 자연스럽게 잇는 방식도 가능해. "
        "같은 문단 안에서 매번 다른 표현을 골라서 써야 해 — 예를 들어 3문장짜리 description에서 세 문장이 전부 \"~추정됩니다\"로 끝나거나, "
        "\"1번째는 추정됩니다, 2번째는 분석됩니다\"처럼 기계적으로 순서를 바꿔가며 반복하는 것도 똑같이 어색하니 피해. "
        "실제 사람이 말하듯 자연스럽고 다양한 추정 표현을 자유롭게 섞어써. "
        "과거 유사 사례의 결과를 인용하는 문장(예: \"그때는 ~로 이어졌다\")만은 예외로 draft 그대로 단정형을 유지해.\n\n"
        "다음 JSON 형식으로만 응답해: "
        '{"causes": [{"cause_name": "설비/공정상의 결함을 요약한 짧은 명사구", "description_draft": "1)의 초안", '
        '"description": "2)의 어조 수정본", "related_variables": ["관련된 변수명"], "link_justification": "", "likelihood_pct": 0}]}\n'
        "related_variables는 반드시 위 목록에 나열된 변수명 중에서만 골라야 하고, 각 원인마다 최소 1개는 있어야 해."
    )

    return _request_items(prompt, "causes")


def generate_quality_impacts(contributing: list[dict]):
    if _client is None:
        return None

    variable_lines = []
    allowed_labels = []
    for v in contributing:
        case = v["case"]
        impact_text = case.quality_impact if case is not None else "알려진 품질 영향 정보 없음"
        tags = list(case.defect_tags) if case is not None else []
        for tag in tags:
            if tag not in allowed_labels:
                allowed_labels.append(tag)
        tag_text = ", ".join(tags) if tags else "없음"
        variable_lines.append(
            f"- {v['variable_name']}: 기준값 대비 {v['direction']}, 기여도 {v['contribution_pct']:.1f}%. "
            f"알려진 품질 영향: {impact_text} / 이 변수에 정의된 불량 유형: {tag_text}"
        )

    prompt = (
        "다음은 제조 공정에서 동시에 발생한 이상 변수 목록과, 각 변수가 기준치를 벗어났을 때 알려진 품질 영향이야.\n\n"
        + "\n".join(variable_lines)
        + "\n\n이 정보들을 종합적으로 분석해서, 지금 이 조합이 실제로 이어질 가능성이 가장 높은 품질/불량 이슈를 "
        "가능성이 높은 순서로 최대 3개까지 골라 순위를 매겨줘. 하나의 변수만으로 설명되는 이슈일 수도 있고, 여러 변수의 품질 영향이 "
        "같은 이슈를 함께 가리키는 경우 그 변수들의 기여도를 종합해서 더 유력한 이슈로 판단할 수도 있어.\n\n"
        "label은 반드시 다음 목록에 있는 문자열 중 하나를 글자 하나 바꾸지 않고 그대로 써야 해: "
        + " | ".join(allowed_labels)
        + "\n이 목록에 없는 표현을 새로 만들거나, 설명 문장의 일부를 잘라내서 라벨로 쓰면 안 돼. "
        "같은 라벨을 두 번 쓰지도 마. 목록에 후보가 3개보다 적으면 있는 개수만큼만 응답해.\n\n"
        "각 이슈마다 그 이슈가 발생할 가능성(likelihood_pct, 0~100 사이 숫자)을 후보 간 비교를 근거로 직접 판단해서 매겨줘. "
        "1순위 > 2순위 > 3순위 순으로 감소해야 해.\n\n"
        "description은 2~3문장으로 써서, 어떤 변수의 어떤 이상이 어떤 물리적 과정을 거쳐 이 이슈로 이어지는지를 설명해. "
        "매우 중요: 데이터의 출처를 언급하면 안 돼. \"CSV에 따르면\", \"CSV 기준 품질 영향에 명시되어 있다\", "
        "\"데이터에 정의된 바와 같이\" 같은 표현은 절대 쓰지 마. 작업자에게 공정 현상을 설명하듯 자연스럽게 써. "
        "모든 문장은 \"~니다\"로 끝나는 존댓말로 써야 해. \"~된다\", \"~한다\", \"~이다\" 같은 평서체로 끝내면 안 돼.\n\n"
        "다음 JSON 형식으로만 응답해: "
        '{"impacts": [{"label": "허용 목록의 라벨 그대로", "description": "물리적 과정을 설명하는 2~3문장", '
        '"related_variables": ["관련된 변수명"], "likelihood_pct": 0}]}\n'
        "related_variables는 반드시 위 목록에 나열된 변수명 중에서만 골라야 하고, 각 이슈마다 최소 1개는 있어야 해."
    )

    return _request_items(prompt, "impacts")


def generate_recommended_actions(entries: list[dict]):
    if _client is None:
        return None

    entry_lines = []
    for i, e in enumerate(entries):
        cause_text = ", ".join(e["cause_names"]) if e["cause_names"] else "관련 원인 미확인"
        past_action_text = (
            f"과거 실제 조치: {e['response']} / 그때의 결과: {e['result']}"
            if e["response"] is not None
            else "일치하는 과거 조치 사례 없음"
        )
        entry_lines.append(
            f"[{i}] 대상 변수: {e['variable_name']} (기준값 대비 {e['direction']}, 기여도 {e['contribution_pct']:.1f}%) / "
            f"이 변수와 관련해 진단된 원인: {cause_text} / {past_action_text}"
        )

    prompt = (
        "다음은 이번 이상 건에서 조치가 필요한 항목들과, 과거에 같은 증상에 대해 숙련자가 실제로 수행했던 조치 기록이야.\n\n"
        + "\n".join(entry_lines)
        + "\n\n작업자는 이 조치들 중 하나를 골라 수행하는 게 아니야. 먼저 1번 조치를 해보고 그것으로 해결되지 않으면 "
        "다음 조치를 시도하는 식으로, 아래에서 정할 순서대로 차례차례 수행하는 것이 기본 대응 방식이야.\n\n"
        "이 점을 감안해서 각 항목에 \"즉시\", \"30분 이내\", \"순차 처리\" 중 하나씩 순서를 배정해줘. "
        "같은 변수에 대한 조치가 여러 개 있으면, 설정값 조정이나 소모품 보충처럼 빠르고 되돌리기 쉬운 조치를 먼저 두고, "
        "부품 교체나 분해 정비처럼 시간과 비용이 큰 근본 조치를 뒤에 둬. "
        "서로 다른 변수에 대한 조치라면 기여도가 높아 영향이 큰 변수를 먼저 처리하도록 배정해. "
        "항목이 3개면 세 등급을 정확히 하나씩만 쓰고, 그보다 적으면 있는 개수만큼 높은 등급부터 순서대로 배정해.\n\n"
        "각 조치의 description은 작업자에게 지시하는 명령형 어조로 써(\"~하십시오\", \"~점검하십시오\", \"~확인하십시오\"). "
        "원인의 발생 메커니즘을 다시 설명하지 말고(그건 이미 다른 화면에 나와 있어), 위에 주어진 과거 실제 조치 내용을 근거로 "
        "지금 무엇을 점검·조정해야 하는지 구체적으로 지시한 뒤, 그때의 결과를 근거로 어떤 상태가 되면 정상화된 것으로 "
        "볼 수 있는지 확인 기준을 함께 제시해. 2~3문장으로 써. "
        "과거 조치 사례가 없는 항목이라면 진단된 원인명을 근거로 일반적인 점검 지시를 명령형으로 써.\n\n"
        "다음 JSON 형식으로만 응답해: "
        '{"actions": [{"action_index": 0, "priority": "즉시", "description": "명령형 지시 2~3문장"}]}\n'
        "action_index는 위 목록의 대괄호 번호와 정확히 일치해야 하고, 모든 항목에 대해 하나씩 빠짐없이 응답해."
    )

    return _request_items(prompt, "actions")
