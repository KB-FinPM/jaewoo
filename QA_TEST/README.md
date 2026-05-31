# OCR result.txt 기반 객관식 QA + 자연어 문제 생성

이 프로그램은 OCR 결과물 `result.txt`를 기준으로 다음 기능을 제공합니다.

1. 객관식 문제를 입력하면 BM25 + 벡터검색으로 보기별 점수를 계산하고 상위 2개 답을 출력
2. M1 MacBook Pro RAM 8GB 환경에 맞춘 최종점수 가중치 적용
3. `jhgan/ko-sroberta-multitask` 임베딩 모델 사용
4. Ollama 로컬 LLM 보정 선택 사용 가능
5. `result.txt` 기준 랜덤 4지선다 문제 생성
6. `--quiz-llm` 사용 시 Ollama 로컬 LLM으로 자연스러운 한국어 문제/보기 생성

## 설치

```bash
pip install -r requirements.txt
```

## 준비

프로그램 파일과 같은 폴더에 OCR 결과 파일을 넣습니다.

```text
result.txt
local_bm25_vector_qa.py
requirements.txt
```

## M1 RAM 8GB 권장 점수 가중치

코드 기본값은 아래와 같습니다.

```python
WEIGHT_BM25 = 0.50
WEIGHT_VECTOR = 0.40
WEIGHT_LLM = 0.10
```

LLM을 끄면 BM25와 VECTOR만 자동 정규화되어 실제 반영 비율은 약 아래와 같습니다.

```text
BM25   : 55.6%
VECTOR : 44.4%
```

OCR 문서는 띄어쓰기나 문장 인식 오류가 있을 수 있어, M1 8GB 환경에서는 벡터검색만 과신하기보다 BM25 키워드 일치도를 약간 더 강하게 반영하는 설정을 추천합니다.

## 객관식 답변 실행

```bash
python local_bm25_vector_qa.py
```

입력 예:

```text
문제내용 중얼중얼
1. 보기1 내용
2. 보기2 내용
3. 보기3 내용
4. 보기4 내용
```

출력 예:

```text
답 : 4번(89%), 3번(10%)
```

점수와 근거를 함께 보려면:

```bash
python local_bm25_vector_qa.py --debug
```

Ollama 보정까지 사용하려면:

```bash
python local_bm25_vector_qa.py --llm
```

기본 Ollama 모델명은 코드 상단의 아래 값입니다.

```python
LLM_MODEL = "qwen:0.5b"
```

설치된 모델명은 아래 명령어로 확인합니다.

```bash
ollama list
```

## 랜덤 문제 10개 생성

LLM 없이 생성:

```bash
python local_bm25_vector_qa.py --quiz 10
```

Ollama 로컬 LLM으로 자연스러운 한국어 문제/보기 생성:

```bash
python local_bm25_vector_qa.py --quiz 10 --quiz-llm
```

특정 모델로 문제 생성:

```bash
python local_bm25_vector_qa.py --quiz 10 --quiz-llm --quiz-model qwen:0.5b
```

`llama3:8b`가 설치되어 있다면 다음처럼 사용할 수 있습니다.

```bash
python local_bm25_vector_qa.py --quiz 10 --quiz-llm --quiz-model llama3:8b
```

생성 결과 파일:

```text
generated_quiz_questions.txt      # 문제만 포함
generated_quiz_answers.txt        # 정답만 포함
generated_quiz_with_answers.txt   # 문제 + 정답 포함
```

항상 같은 문제를 재생성하려면 seed를 지정합니다.

```bash
python local_bm25_vector_qa.py --quiz 10 --seed 1234
```

## 인덱스 강제 재생성

`result.txt`를 바꿨거나 모델명을 변경했다면:

```bash
python local_bm25_vector_qa.py --rebuild
```

## 현재 기본 모델

```python
EMBED_MODEL_NAME = "jhgan/ko-sroberta-multitask"
```

M1 MacBook Pro RAM 8GB 환경에서는 이 모델과 BM25 조합을 우선 추천합니다.
