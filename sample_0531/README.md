# PM Agent

구축요건정의서 DOCX를 분석해 다음 산출물을 생성합니다.

- `output/프로젝트명_요구사항명세서_v.0.1.xlsx`
- `output/프로젝트명_WBS_v.0.1.xlsx`
- `output/프로젝트명_화면기획서_v.0.1.pptx`

프로젝트명 공백은 `_`로 치환되며, 동일 파일이 있으면 `v.0.2`, `v.0.3` 순서로 자동 증가합니다.

## 실행 준비

```bash
pip install -r requirements.txt
```

Qdrant 실행:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

AWS 인증:

```bash
aws configure
```

프로젝트 input 폴더에 버전이 포함된 파일을 넣습니다.

```text
input/구축요건정의서.v.1.docx
input/구축요건정의서.v.2.docx
```

`--docx`를 생략하면 `input/구축요건정의서.v.#.docx` 중 숫자 버전이 가장 높은 파일을 자동으로 읽습니다.

```bash
python main.py
```

특정 파일을 강제로 분석하려면 `--docx`를 지정합니다.

```bash
python main.py --docx input/구축요건정의서.v.1.docx
```

프로젝트명, 작성자, mapper 파일을 지정해서 실행할 수 있습니다.

```bash
python main.py \
  --project-name "테스트 프로젝트" \
  --author "홍길동" \
  --mapper template/output_mapper.json
```

## Mapper 설정

입력 문서 선택 기준, 산출물의 템플릿 경로, 시트명, 컬럼명, PPT 슬라이드 번호, placeholder, Description 표 위치는 소스가 아니라 아래 JSON에서 관리합니다.

```text
template/output_mapper.json
```

`input_document.input_dir`, `input_document.base_name`을 수정하면 자동 선택 대상 문서명을 바꿀 수 있습니다.

예를 들어 요구사항명세서의 입력 열이 바뀌면 `requirement_spec.data_sheet.columns`의 `header_names` 또는 `default_column`만 수정하면 됩니다.

WBS 입력 열은 `wbs.data_sheet.columns`에서 변경합니다.

화면기획서의 반복 기준 슬라이드나 Description 표 설정은 `screen_plan.template_slide_index`, `screen_plan.description_table`에서 변경합니다.

동일 버전 파일이라도 파일명, 생성/metadata 변경시각, 수정시각, 파일 용량, SHA-256 해시가 모두 같을 때만 기존 분석 결과를 사용합니다. 하나라도 다르면 새 파일로 판단해 Bedrock 분석을 다시 수행합니다.
