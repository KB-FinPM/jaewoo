# PM Agent

## 실행 준비

```bash
pip install -r requirements.txt
cp .env.example .env
```

Qdrant 실행:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

AWS 인증:

```bash
aws configure
```

프로젝트 루트에 `구축요건정의서.docx` 파일을 넣고 실행합니다.

```bash
python main.py
```

## 출력

- `output/요구사항명세서.xlsx`
- `output/WBS.xlsx`


## Token Usage

실행 완료 후 Bedrock 사용량을 출력합니다.

```text
[Token Usage Summary]
- Bedrock calls : 00
- Input tokens  : 00
- Output tokens : 00
- Total tokens  : 00
```
