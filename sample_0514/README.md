# PM Agent

구축요건정의서 DOCX를 분석해 다음 산출물을 생성합니다.

- `output/요구사항명세서.xlsx`
- `output/WBS.xlsx`
- `output/화면기획서.pptx`

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

프로젝트 루트에 버전이 포함된 파일을 넣습니다.

```text
구축요건정의서.v.1.docx
```

실행:

```bash
python main.py --docx 구축요건정의서.v.1.docx
```

동일 버전 파일이 이미 분석된 경우 Bedrock 분석을 다시 수행하지 않고 `output/cache`의 기존 분석 결과를 사용합니다.
