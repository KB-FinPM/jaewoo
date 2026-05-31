# PM Agent 프로세스 설명

## 1. 전체 흐름

```text
main.py
 -> template/output_mapper.json 로드
 -> pipeline.run_pipeline()
 -> input/구축요건정의서.v.#.docx 중 최신 숫자 버전 자동 선택
 -> 문서 버전 확인
 -> 기존 분석 여부 확인
 -> DOCX 읽기
 -> Semantic Chunking
 -> Bedrock 요구사항 Atom 추출
 -> Qdrant 저장
 -> RAG 검색 기반 산출물 데이터 생성
    -> 요구사항 Atom
    -> WBS 항목
    -> 화면설계 항목
 -> mapper 기준으로 템플릿 파일에 데이터 입력
    -> 요구사항명세서 Excel
    -> WBS Excel
    -> 화면기획서 PowerPoint
 -> mapper 기준 파일명 생성
    -> output/프로젝트명_요구사항명세서_v.0.1.xlsx
    -> output/프로젝트명_WBS_v.0.1.xlsx
    -> output/프로젝트명_화면기획서_v.0.1.pptx
    -> 동일 파일명이 있으면 v.0.2, v.0.3 ... 으로 자동 증가
 -> 토큰 사용량 출력
```

## 2. Mapper 분리 방식

기존에는 시트명, 컬럼 위치, PPT 슬라이드 번호, placeholder가 소스에 직접 들어가 있었습니다.
현재는 아래 JSON 파일에서 산출물 매핑 정보를 관리합니다.

```text
template/output_mapper.json
```

소스를 수정하지 않고 JSON만 수정해 다음 내용을 변경할 수 있습니다.

- 요구사항명세서 템플릿 경로
- 요구사항명세서 표지/개정이력 placeholder
- 요구사항명세서 데이터 시트명, header row, start row, 입력 컬럼
- WBS 템플릿 경로
- WBS 데이터 시트명, header row, start row, 입력 컬럼
- 화면기획서 템플릿 경로
- 공통 치환 슬라이드 번호
- 반복 기준 슬라이드 번호
- 화면별 placeholder 매핑
- Description 표 식별 조건, 입력 행/열, 최대 입력 건수, 출력 문장 형식
- input 문서 자동 선택 기준
- output 파일명 규칙

## 3. 주요 Mapper 구조


### 3.0 input_document

```json
{
  "input_document": {
    "input_dir": "input",
    "base_name": "구축요건정의서",
    "version_pattern": "{base_name}.v.{version}.docx",
    "version_type": "integer_highest"
  }
}
```

`--docx`를 지정하지 않으면 `input_dir` 아래에서 `base_name.v.#.docx` 형식의 파일을 찾고, 숫자 버전이 가장 높은 파일을 분석 대상으로 선택합니다.

### 3.1 output_files

```json
{
  "output_files": {
    "initial_major": 0,
    "initial_minor": 1,
    "space_replacement": "_",
    "documents": {
      "requirement_spec": {
        "document_name": "요구사항명세서",
        "extension": ".xlsx"
      },
      "wbs": {
        "document_name": "WBS",
        "extension": ".xlsx"
      },
      "screen_plan": {
        "document_name": "화면기획서",
        "extension": ".pptx"
      }
    }
  }
}
```

### 3.2 요구사항명세서

```json
{
  "requirement_spec": {
    "template_path": "template/탬플릿_요구사항명세서.xlsx",
    "placeholder_sheets": [],
    "data_sheet": {
      "sheet_name": "요구사항명세서",
      "header_row": 1,
      "start_row": 2,
      "columns": []
    }
  }
}
```

컬럼은 `field`, `header_names`, `default_column`으로 구성합니다.
`header_names`로 먼저 찾고, 못 찾으면 `default_column`을 사용합니다.

예시:

```json
{
  "field": "note|description",
  "header_names": ["검토의견"],
  "default_column": 16
}
```

`note|description`은 `note` 값이 있으면 `note`, 없으면 `description`을 사용한다는 의미입니다.

### 3.3 WBS

```json
{
  "wbs": {
    "template_path": "template/탬플릿_WBS.xlsx",
    "data_sheet": {
      "sheet_name": "WBS",
      "header_row": 1,
      "start_row": 2,
      "columns": []
    }
  }
}
```

`row_number` 필드는 데이터 순번을 자동 입력합니다.

### 3.4 화면기획서

```json
{
  "screen_plan": {
    "template_path": "template/탬플릿_화면설계서.pptx",
    "common_slide_indices": [0, 1],
    "template_slide_index": 2,
    "placeholder_slides": {
      "common": {},
      "screen_item": {}
    },
    "description_table": {}
  }
}
```

`common_slide_indices`는 프로젝트명, 작성자, 작성일 같은 공통 값을 치환할 슬라이드 번호입니다.

`template_slide_index`는 화면설계 항목마다 복제할 기준 슬라이드 번호입니다.

`description_table.max_items`는 Description 표에 입력할 최대 건수입니다. 현재 기본값은 10입니다.

## 4. RAG 적용 방식

1. `input/구축요건정의서.v.#.docx` 중 숫자 버전이 가장 높은 파일을 읽습니다. 단, `--docx`를 지정하면 해당 파일을 우선 사용합니다.
2. 구축요건정의서 본문을 의미 단위 chunk로 분할합니다.
3. 각 chunk에서 Bedrock을 이용해 요구사항 Atom을 추출합니다.
4. 추출한 Atom을 embedding하여 Qdrant에 저장합니다.
5. WBS와 화면설계서 생성 시 Qdrant에서 관련 요구사항만 검색합니다.
6. 검색된 요구사항을 Bedrock에 전달하여 WBS 항목과 화면설계 항목을 생성합니다.
7. 생성된 데이터를 mapper 기준으로 각 템플릿 파일에 입력해 최종 산출물을 저장합니다.

## 5. 버전 관리 방식

파일명은 다음 형식을 권장합니다.

```text
구축요건정의서.v.1.docx
구축요건정의서.v.2.docx
```

동일 버전이 `output/cache/doc_versions.json`에 존재하더라도 아래 값이 모두 같을 때만 기존 분석 결과를 사용합니다.

- 파일명
- 문서 key
- 생성/metadata 변경시각
- 수정시각
- 파일 용량
- SHA-256 파일 해시

파일명이 같아도 내용이 바뀌어 파일 용량, 수정시각, 해시 등이 달라지면 새 파일로 판단해 재분석합니다.

동일 파일로 확인되면 다음 메시지를 출력합니다.

```text
동일 파일로 확인되어 기존 분석 결과를 사용합니다.
```

파일명이 같지만 실제 파일이 달라진 경우 다음 메시지를 출력하고 재분석합니다.

```text
파일명은 같지만 생성/수정시각, 파일용량 또는 해시가 달라 새 파일로 판단했습니다. 재분석합니다.
```

## 6. 실행 옵션

```bash
python main.py \
  --docx input/구축요건정의서.v.1.docx \
  --output-dir output \
  --project-name "프로젝트명" \
  --author "작성자" \
  --mapper template/output_mapper.json
```

`.env`에서도 기본 mapper 경로를 지정할 수 있습니다.

```text
OUTPUT_MAPPER_PATH=template/output_mapper.json
```

## 7. 주요 모듈

| 모듈 | 역할 |
|---|---|
| `main.py` | CLI 실행 진입점 |
| `modules/pipeline.py` | 전체 프로세스 오케스트레이션 |
| `modules/mapper_loader.py` | JSON mapper 로드, 경로 보정, field 값 추출 |
| `modules/excel_writer.py` | mapper 기반 Excel 템플릿 입력 |
| `modules/ppt_writer.py` | mapper 기반 PowerPoint 템플릿 입력 |
| `modules/version_manager.py` | 문서 버전, 파일 해시, 캐시 관리 |
| `modules/docx_reader.py` | DOCX 문단/표 텍스트 추출 |
| `modules/chunker.py` | heading 및 길이 기준 chunk 분할 |
| `modules/extractor.py` | Bedrock으로 요구사항 Atom 추출 |
| `modules/qdrant_store.py` | Qdrant 저장/검색/스크롤 |
| `modules/rag_service.py` | 도메인별 RAG 검색 로직 |
| `modules/wbs_generator.py` | RAG 기반 WBS 생성 |
| `modules/screen_planner.py` | RAG 기반 화면설계 데이터 생성 |
| `modules/token_tracker.py` | Bedrock token 사용량 집계 |
| `modules/logger_utils.py` | `[HH:MM:SS]` 로그 출력 |

## 8. 생성 산출물

```text
output/
 ├─ 프로젝트명_요구사항명세서_v.0.1.xlsx
 ├─ 프로젝트명_WBS_v.0.1.xlsx
 └─ 프로젝트명_화면기획서_v.0.1.pptx
```

파일 생성 시 프로젝트명의 공백은 `_`로 치환합니다.
동일한 파일이 이미 있으면 기존 파일을 덮어쓰지 않고 minor version을 1 증가시켜 저장합니다.
