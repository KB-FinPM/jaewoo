# PM Agent 프로세스 설명

## 1. 전체 흐름

```text
main.py
 -> pipeline.run_pipeline()
 -> 문서 버전 확인
 -> 기존 분석 여부 확인
 -> DOCX 읽기
 -> Semantic Chunking
 -> Bedrock 요구사항 Atom 추출
 -> Qdrant 저장
 -> RAG 검색 기반 산출물 생성
    -> 요구사항명세서.xlsx
    -> WBS.xlsx
    -> 화면기획서.pptx
 -> 토큰 사용량 출력
```

## 2. RAG 적용 방식

1. 구축요건정의서를 chunk 단위로 분할합니다.
2. 각 chunk에서 요구사항 Atom을 추출합니다.
3. Atom을 embedding하여 Qdrant에 저장합니다.
4. WBS와 화면기획서 생성 시 Qdrant에서 관련 요구사항만 검색합니다.
5. 검색된 요구사항만 Bedrock에 전달하여 산출물을 생성합니다.

## 3. 버전 관리 방식

파일명은 다음 형식을 권장합니다.

```text
구축요건정의서.v.1.docx
구축요건정의서.v.2.docx
```

동일 버전이 `output/cache/doc_versions.json`에 존재하면 문서를 다시 분석하지 않고 기존 분석 결과를 사용합니다.

## 4. 주요 모듈

| 모듈 | 역할 |
|---|---|
| `main.py` | CLI 실행 진입점 |
| `modules/pipeline.py` | 전체 프로세스 오케스트레이션 |
| `modules/version_manager.py` | 문서 버전, 파일 해시, 캐시 관리 |
| `modules/docx_reader.py` | DOCX 문단/표 텍스트 추출 |
| `modules/chunker.py` | heading 및 길이 기준 chunk 분할 |
| `modules/extractor.py` | Bedrock으로 요구사항 Atom 추출 |
| `modules/qdrant_store.py` | Qdrant 저장/검색/스크롤 |
| `modules/rag_service.py` | 도메인별 RAG 검색 로직 |
| `modules/wbs_generator.py` | RAG 기반 WBS 생성 |
| `modules/screen_planner.py` | RAG 기반 화면기획 데이터 생성 |
| `modules/excel_writer.py` | 요구사항명세서/WBS Excel 생성 |
| `modules/ppt_writer.py` | 화면기획서 PowerPoint 생성 |
| `modules/token_tracker.py` | Bedrock token 사용량 집계 |
| `modules/logger_utils.py` | `[HH:MM:SS]` 로그 출력 |

## 5. 산출물

### 요구사항명세서.xlsx
- 구분
- 요구사항ID
- 요구사항명
- 기능/비기능요구사항
- 비고

### WBS.xlsx
- 레벨
- WBS명
- 시작예정일
- 종료예정일
- 작업자
- 산출물

### 화면기획서.pptx
- 상단: 요구사항ID, 화면번호, 화면명
- 중앙: 화면 기획 이미지 삽입용 빈 영역
- 우측: 해당 화면에서 표시해야 할 내용 표
