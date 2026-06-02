# CHANGELOG

backend.zip 기준으로 PM 산출물 생성 기능을 통합한 변경 내역입니다.

## 통합 기준

- 기존 backend 구조 유지
- `pm_*.py` 분리 파일 제거
- 기존 표준 파일에 주석과 함께 통합
- PM 산출물 생성 기능 유지

## 전체 구조 및 변경 내역

```text
pm-agent/
├── app/
│   ├── api/
│   │   ├── artifacts.py
│   │   ├── documents.py
│   │   ├── generation.py (변경) PM 생성 API 통합
│   │   ├── health.py
│   │   ├── templates.py
│   │   ├── traceability.py
│   │   └── upload.py
│   │
│   ├── orchestrator/
│   │   ├── document_ingestion_orchestrator.py
│   │   ├── generation_orchestrator.py (변경) PM 파이프라인 통합
│   │   ├── input_orchestrator.py (변경) 문서입력 흐름 추가
│   │   └── output_orchestrator.py (변경) 파일출력 흐름 추가
│   │
│   ├── agents/
│   │   ├── AGENT_DEVELOPMENT.md
│   │   ├── core_agents/
│   │   │   ├── requirement_agent/
│   │   │   │   ├── AGENT.md (추가) 요구사항 지침
│   │   │   │   └── agent.py (변경) 문서기반 추출
│   │   │   ├── wbs_agent/ (추가) WBS 생성 Agent
│   │   │   │   ├── AGENT.md (추가) WBS 지침
│   │   │   │   ├── agent.py (추가) WBS 실행
│   │   │   │   └── generator.py (추가) WBS 생성로직
│   │   │   ├── storyboard_agent/ (추가) 화면기획 Agent
│   │   │   │   ├── AGENT.md (추가) 화면기획 지침
│   │   │   │   ├── agent.py (추가) 화면 실행
│   │   │   │   └── planner.py (추가) 화면 생성로직
│   │   │   └── validator_agent/
│   │   │       ├── __init__.py (추가) 패키지 초기화
│   │   │       └── agent.py
│   │   │
│   │   ├── input_agents/
│   │   │   └── document_parser_agent/
│   │   │       ├── AGENT.md (추가) 문서파싱 지침
│   │   │       ├── agent.py (변경) DOCX 분석 연결
│   │   │       └── extractor.py (추가) 요구사항 추출
│   │   │
│   │   └── output_agents/
│   │       ├── markdown_agent/
│   │       │   ├── AGENT.md (추가) Markdown 지침
│   │       │   └── summary_agent.py (추가) 요약 생성
│   │       ├── requirement_spec_agent/ (추가) 요구사항 출력
│   │       │   ├── AGENT.md (추가) 엑셀출력 지침
│   │       │   └── agent.py (추가) 요구사항 엑셀
│   │       ├── wbs_output_agent/ (추가) WBS 출력
│   │       │   ├── AGENT.md (추가) WBS출력 지침
│   │       │   └── agent.py (추가) WBS 엑셀
│   │       └── screen_plan_agent/ (추가) 화면기획 출력
│   │           ├── AGENT.md (추가) PPT출력 지침
│   │           └── agent.py (추가) 화면 PPT
│   │
│   ├── rag/
│   │   ├── chunking.py (변경) 의미기반 chunk 추가
│   │   ├── retrieval.py
│   │   ├── qdrant_store.py (추가) Qdrant 저장소
│   │   └── rag_service.py (추가) RAG 검색 서비스
│   │
│   ├── storage/
│   │   ├── s3.py
│   │   ├── docx_reader.py (추가) DOCX 텍스트 추출
│   │   ├── excel_writer.py (추가) 템플릿 엑셀 출력
│   │   ├── ppt_writer.py (추가) 템플릿 PPT 출력
│   │   ├── file_version.py (추가) 결과파일 버전관리
│   │   └── version_manager.py (추가) 입력파일 식별
│   │
│   ├── schemas/
│   │   ├── agent.py
│   │   ├── artifact.py (변경) PM 산출물 모델 추가
│   │   ├── io_agent.py
│   │   ├── request.py (변경) PM 요청 모델 추가
│   │   ├── response.py (변경) PM 응답 모델 추가
│   │   ├── requirement.py
│   │   ├── template.py
│   │   └── traceability.py
│   │
│   ├── core/
│   │   ├── config.py (변경) PM 환경설정 통합
│   │   ├── logger.py (변경) 단계로그 함수 추가
│   │   ├── llm.py
│   │   ├── agent_instruction.py (추가) AGENT.md 로더
│   │   ├── bedrock_client.py (추가) Bedrock 호출
│   │   ├── json_utils.py (추가) JSON 보정 유틸
│   │   ├── mapper_loader.py (추가) mapper 로더
│   │   ├── process_loader.py (추가) process 로더
│   │   └── token_tracker.py (추가) 토큰 사용량 추적
│   │
│   ├── db/
│   ├── models/
│   ├── repositories/
│   ├── services/
│   └── main.py (변경) generation 라우터 유지
│
├── template/ (추가) 산출물 템플릿
│   ├── output_mapper.json (추가) 출력 매핑 설정
│   ├── 탬플릿_요구사항명세서.xlsx
│   ├── 탬플릿_WBS.xlsx
│   └── 탬플릿_화면설계서.pptx
│
├── input/ (추가) 입력 DOCX 위치
├── output/ (추가) 결과물 생성 위치
├── process.json (추가) Agent 실행 제어
├── docker-compose.yml (추가) Qdrant 실행환경
├── run_pm_pipeline.py (추가) 로컬 파이프라인
├── PROCESS.md (추가) PM 처리절차 문서
├── CHANGELOG.md (추가) 통합 변경내역
├── README.md (변경) PM 실행방법 추가
├── requirements.txt (변경) PM 의존성 추가
└── run.sh
```

## 주요 통합 내용

```text
pm_config.py 제거      → core/config.py 통합
pm_logger.py 제거      → core/logger.py 통합
pm_artifacts.py 제거   → api/generation.py 통합
pm_pipeline.py 제거    → generation_orchestrator.py 통합
pm_chunking.py 제거    → rag/chunking.py 통합
pm_artifacts schema 제거 → schemas/artifact.py 통합
```

## 실행 API

```text
POST /generate/pm-artifacts
```

## 로컬 실행

```bash
python run_pm_pipeline.py --project-name "테스트 프로젝트" --author "홍길동"
```

## Token limit update

```text
process.json (변경) max_token 설정 추가
app/core/token_limiter.py (추가) 토큰 제한 공통 유틸
app/core/process_loader.py (변경) max_token 로딩 반영
app/core/bedrock_client.py (변경) 입출력 토큰 제한 적용
app/core/llm.py (변경) 공통 LLM 토큰 제한 적용
app/core/json_utils.py (변경) JSON 복구 입력 제한 적용
```


## Token 제한 정책 변경

app/core/bedrock_client.py (변경) JSON 응답 절단 제거
app/core/json_utils.py (변경) 복구 JSON 절단 제거
app/core/token_limiter.py (변경) output 전용 제한
app/storage/excel_writer.py (변경) Excel 출력 제한 적용
app/storage/ppt_writer.py (변경) PPT 출력 제한 적용
README.md (변경) 로컬 실행 예시 수정
process.json (변경) max_token 주석 추가
