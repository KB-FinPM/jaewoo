# PM Agent

구축요건정의서(`input/구축요건정의서.v.#.docx`)를 분석하여 다음 산출물을 생성합니다.

- 요구사항명세서
- WBS
- 화면기획서

backend/FastAPI 구조 통합 전 단계의 standalone 실행 소스입니다.

---

## 주요 기능

```text
구축요건정의서.v.#.docx
  ↓
최신 버전 자동 선택
  ↓
파일 동일성 확인
  - 파일명
  - 버전
  - 용량
  - 생성/수정시각
  - SHA256
  ↓
DOCX 파싱
  ↓
Semantic Chunking
  ↓
Bedrock 요구사항 추출
  ↓
PgVector 저장/RAG 검색
  ↓
요구사항명세서 / WBS / 화면기획서 생성
```

---

## 로컬 실행

```bash
python main.py --project-name "프로젝트명" --author "작성자"
```

특정 문서를 지정하려면:

```bash
python main.py \
  --docx input/구축요건정의서.v.2.docx \
  --project-name "프로젝트명" \
  --author "작성자"
```

---

## 설정 파일

### process.json

산출물 생성 여부, 프로젝트 유형, 출력 토큰 제한을 제어합니다.

```json
{
  "project_type": "auto",
  "max_token": 1000,
  "steps": [
    {"id": "requirement_spec", "enabled": true},
    {"id": "wbs", "enabled": true},
    {"id": "screen_plan", "enabled": true}
  ]
}
```

`max_token`은 최종 산출물에 입력되는 긴 텍스트에만 적용합니다. JSON 응답과 JSON 복구에는 적용하지 않습니다.

### template/output_mapper.json

템플릿 경로, 시트명, 컬럼명, PPT 슬라이드/placeholder/Description 표 매핑을 관리합니다.

### template/wbs_template.json

WBS No 1~36 공통 템플릿을 관리합니다.

### template/deliverable_mapper.json

Biz요건명/단계 키워드에 따른 산출물 매핑을 관리합니다.

---

## 프로젝트 유형

`process.json`의 `project_type` 값으로 제어합니다.

```text
auto         자동 판별
infra        인프라 구축 프로젝트
development  애플리케이션 개발 프로젝트
hybrid       인프라+개발 혼합 프로젝트
```

---

## Agent 지침

각 Agent별 지침은 아래 파일을 읽어 프롬프트에 포함합니다.

```text
agents/
 ├─ requirement_agent/AGENT.md
 ├─ wbs_agent/AGENT.md
 └─ storyboard_agent/AGENT.md
```

---

## 출력 파일명

프로젝트명 공백은 `_`로 치환하고, 기존 파일이 있으면 버전을 자동 증가합니다.

```text
프로젝트명_요구사항명세서_v.0.1.xlsx
프로젝트명_WBS_v.0.1.xlsx
프로젝트명_화면기획서_v.0.1.pptx
```
