# PROCESS

## 1. 입력 문서 선택

`input/구축요건정의서.v.#.docx` 중 버전 숫자가 가장 높은 파일을 자동 선택합니다.

수동 지정 시 `--docx` 인자를 우선 사용합니다.

## 2. 동일 파일 판단

다음 값이 모두 같으면 기존 분석 결과를 재사용합니다.

```text
파일명
문서명
버전
파일 용량
생성/metadata 변경시각
수정시각
SHA256 해시
```

하나라도 다르면 재분석합니다.

## 3. 요구사항 추출

DOCX를 읽고 semantic chunk로 분리한 뒤, Bedrock을 통해 요구사항 Atom을 추출합니다.

추출 기준은 다음 Agent 지침을 포함합니다.

```text
agents/requirement_agent/AGENT.md
```

요구사항은 Biz요건명 중심으로 그룹화합니다.

## 4. PgVector 저장/RAG

추출된 요구사항은 PgVector에 저장합니다.

WBS/화면기획서 생성 시 Biz요건명 또는 domain 기준으로 RAG 검색을 수행합니다.

## 5. 산출물 생성 제어

`process.json`의 steps 설정에 따라 산출물 생성 여부를 제어합니다.

```json
{"id":"wbs", "enabled":true}
```

## 6. 요구사항명세서 생성

`template/output_mapper.json`의 `requirement_spec` 설정을 사용합니다.

템플릿:

```text
template/탬플릿_요구사항명세서.xlsx
```

## 7. WBS 생성

WBS는 다음 규칙으로 생성합니다.

```text
0레벨: 프로젝트명
No 1~36: template/wbs_template.json 공통항목
No 37~: Biz요건명 기준 자동 생성
```

프로젝트 유형에 따라 단계명을 다르게 사용합니다.

```text
infra: 분석, 설계, 개발환경 구축, 스테이징 구축, 운영 구축
development: 분석, 설계, 개발, 테스트, 운영 이행
hybrid: 분석, 설계, 개발/구축, 스테이징 검증, 운영 이행
```

산출물은 `template/deliverable_mapper.json` 기준으로 명확한 항목만 매핑합니다.

## 8. 화면기획서 생성

화면과 직접 관련 있는 요구사항만 화면기획 대상으로 사용합니다.

PPT 템플릿의 Description 영역은 기존 폰트/스타일을 유지하며 텍스트만 교체합니다.

## 9. 출력 토큰 제한

`process.json`의 `max_token`은 최종 산출물 텍스트 입력 시점에만 적용합니다.

JSON 응답/복구 단계에는 적용하지 않습니다.
