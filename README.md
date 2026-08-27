# MAITECH

AI 기반 제조 공정관리 MVP. 이상탐지 → 원인분석 → 품질예측 → 예상 품질영향 → 권장조치 → 조치기록 → 관리자 확인까지 전 구간이 동작하는 프로토타입입니다.

## 구성

- `backend/` — FastAPI + SQLite 백엔드
- `frontend/` — 순수 HTML/CSS/JS 프론트엔드

## 로컬 실행 방법

### 1. 백엔드

```bash
cd backend
python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

./venv/Scripts/python.exe scripts/seed.py                      # DB 초기화 + 샘플 시나리오 시딩
./venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

백엔드는 `http://localhost:8000`에서 동작합니다.

AI 원인분석/권장조치 설명 문장 생성에 Gemini API를 사용합니다. `backend/.env`에 아래와 같이 키를 넣으면 활성화되고, 없으면 규칙 기반 설명으로 자동 대체됩니다 

```
GEMINI_API_KEY=your-key-here
```

### 2. 프론트엔드

정적 파일 서버로 `frontend/` 디렉터리를 서빙하면 됩니다. 예:

```bash
npx serve frontend -l 5173
```

브라우저에서 `http://localhost:5173/index.html` 접속.

### 3. 로그인 계정

시딩 시 아래 두 계정이 생성됩니다.

| 역할 | 아이디 | 비밀번호 |
|------|--------|----------|
| 작업자 | worker1 | worker1234 |
| 관리자 | manager1 | manager1234 |

### 4. 시나리오 재생

로그인 후 헤더의 "시작" 버튼을 누르면 샘플 시나리오(4개 호기)가 5배속으로 재생되며 이상탐지가 시작됩니다. "일시정지/재생"으로 흐름을 멈추거나 다시 재생할 수 있고, "재시작"을 누르면 해당 시나리오의 이상 건·AI 캐시·조치기록을 모두 지우고 처음부터 다시 재생합니다.
