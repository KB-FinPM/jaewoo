# PM Multi-Agent 처리 프로세스

## 전체 흐름

```text
main.py
  ↓
process.json 로딩
  ↓
template/output_mapper.json 로딩
  ↓
Input Orchestrator
  ↓
Document Parser Agent
  ↓
Qdrant 저장 / 기존 분석 결과 조회
  ↓
Core Orchestrator
  ├─ Requirement Agent
  ├─ WBS Agent
  └─ Storyboard Agent
  ↓
Output Orchestrator
  ├─ Requirement Spec Output Agent
  ├─ WBS Output Agent
  ├─ Screen Plan Output Agent
  └─ Markdown Agent
  ↓
output/ 산출물 생성
```

## 1. process.json 기반 실행 제어

`process.json`의 `enabled` 값을 기준으로 Agent와 산출물 생성을 제어합니다.

예시:

```json
"output_agents": {
  "requirement_spec": { "enabled": true },
  "wbs": { "enabled": false },
  "screen_plan": { "enabled": true }
}
```

위 설정이면 요구사항명세서와 화면기획서만 생성하고 WBS는 생성하지 않습니다.

## 2. 입력 문서 선택

문서 경로를 명시하지 않으면 아래 패턴에서 숫자 버전이 가장 높은 파일을 선택합니다.

```text
input/구축요건정의서.v.#.docx
```

예:

```text
구축요건정의서.v.1.docx
구축요건정의서.v.2.docx
```

위 두 파일이 있으면 `v.2`를 분석합니다.

## 3. 동일 파일 판단

동일 파일 여부는 파일명만 보지 않고 아래 값을 함께 비교합니다.

- 파일명
- 문서 key
- 파일 크기
- 생성/metadata 변경 시각
- 수정 시각
- SHA-256 해시

하나라도 다르면 새 파일로 판단하고 재분석합니다.

## 4. Qdrant / RAG

Qdrant는 요구사항 atom 저장과 RAG 검색에 사용합니다.

실행:

```bash
docker compose up -d qdrant
```

확인:

```bash
curl http://localhost:6333/collections
```

Document Parser Agent는 추출한 요구사항 atom을 Qdrant에 저장합니다.
WBS Agent와 Storyboard Agent는 Qdrant에서 도메인별 관련 요구사항을 검색해 산출물 생성을 수행합니다.

## 5. Agent별 Markdown 지침

각 Agent는 자신과 같은 폴더의 `AGENT.md`를 읽습니다.

```text
agents/input_agents/document_parser_agent/AGENT.md
agents/core_agents/requirement_agent/AGENT.md
agents/core_agents/wbs_agent/AGENT.md
agents/core_agents/storyboard_agent/AGENT.md
agents/output_agents/requirement_spec_agent/AGENT.md
agents/output_agents/wbs_output_agent/AGENT.md
agents/output_agents/screen_plan_agent/AGENT.md
agents/output_agents/markdown_agent/AGENT.md
```

LLM을 호출하는 Agent는 `AGENT.md` 내용을 system prompt에 포함합니다.
출력 Agent는 `AGENT.md`를 실행 규칙 문서로 읽어둡니다.

## 6. mapper 기반 산출물 생성

산출물 템플릿, 시트명, 컬럼명, PPT placeholder는 아래 파일에서 관리합니다.

```text
template/output_mapper.json
```

소스에 시트명/컬럼명/placeholder를 하드코딩하지 않고 mapper 설정을 따릅니다.

## 7. 산출물 파일명 버전 증가

파일명 규칙:

```text
프로젝트명_요구사항명세서_v.0.1.xlsx
프로젝트명_WBS_v.0.1.xlsx
프로젝트명_화면기획서_v.0.1.pptx
```

프로젝트명 공백은 `_`로 치환합니다.
동일 파일명이 있으면 `v.0.2`, `v.0.3`처럼 minor 버전을 증가시킵니다.
