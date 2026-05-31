import argparse
import json
import math
import os
import pickle
import random
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import faiss
import numpy as np
import requests
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

TEXT_FILE = "result.txt"
INDEX_FILE = "result.faiss"
CHUNKS_FILE = "chunks.pkl"
BM25_FILE = "bm25.pkl"
META_FILE = "meta.json"

EMBED_MODEL_NAME = "jhgan/ko-sroberta-multitask"

# Ollama는 선택 사항입니다. LLM 없이도 BM25+벡터검색 점수만으로 답을 냅니다.
USE_LLM = False
OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen:0.5b"

CHUNK_SIZE = 700
CHUNK_OVERLAP = 120
TOP_K = 8

# 최종 점수 가중치. M1 MacBook Pro RAM 8GB + jhgan/ko-sroberta-multitask 기준 권장값입니다.
# LLM을 끄면 BM25 0.50 / VECTOR 0.40이 자동 정규화되어 실제로는 약 BM25 55.6%, VECTOR 44.4%로 반영됩니다.
# 이유: 8GB 환경에서는 벡터 의미검색만 과신하지 않고, OCR 원문과 보기의 키워드 일치도를 조금 더 강하게 반영하는 편이 안정적입니다.
WEIGHT_BM25 = 0.50
WEIGHT_VECTOR = 0.40
WEIGHT_LLM = 0.10


@dataclass
class SearchHit:
    chunk_id: int
    bm25_score: float
    vector_score: float
    hybrid_score: float
    text: str


def log(message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {message}")


def read_text(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_path} 파일이 없습니다. OCR 결과 파일을 같은 폴더에 넣어주세요.")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    """한국어 형태소 분석기 없이도 동작하는 간단 토크나이저입니다."""
    text = normalize_text(text).lower()
    tokens = re.findall(r"[가-힣a-zA-Z0-9]+", text)
    char_terms: list[str] = []
    compact = "".join(tokens)
    # OCR 텍스트에서는 띄어쓰기 품질이 낮을 수 있어 2~3글자 n-gram도 같이 사용합니다.
    for n in (2, 3):
        if len(compact) >= n:
            char_terms.extend(compact[i:i + n] for i in range(len(compact) - n + 1))
    return tokens + char_terms


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = normalize_text(text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= chunk_size:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            current = paragraph
            while len(current) > chunk_size:
                chunks.append(current[:chunk_size])
                current = current[chunk_size - overlap:]

    if current:
        chunks.append(current)

    return [c for c in chunks if len(c.strip()) >= 20]


def file_signature(file_path: str) -> dict[str, Any]:
    stat = os.stat(file_path)
    return {
        "file_path": file_path,
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embed_model": EMBED_MODEL_NAME,
    }


def is_index_current() -> bool:
    required = [INDEX_FILE, CHUNKS_FILE, BM25_FILE, META_FILE, TEXT_FILE]
    if not all(os.path.exists(path) for path in required):
        return False
    try:
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f) == file_signature(TEXT_FILE)
    except Exception:
        return False


def load_embedder() -> SentenceTransformer:
    log(f"임베딩 모델 로딩: {EMBED_MODEL_NAME}")
    return SentenceTransformer(EMBED_MODEL_NAME)


def build_index(force: bool = False) -> None:
    if not force and is_index_current():
        log("기존 인덱스를 사용합니다. result.txt 변경 없음")
        return

    log("result.txt 읽는 중")
    text = read_text(TEXT_FILE)
    chunks = split_text(text)
    if not chunks:
        raise ValueError("result.txt에서 유효한 텍스트 조각을 만들 수 없습니다.")

    tokenized_chunks = [tokenize(chunk) for chunk in chunks]
    bm25 = BM25Okapi(tokenized_chunks)

    embedder = load_embedder()
    log(f"텍스트 조각 {len(chunks)}개 임베딩 생성 중")
    vectors = embedder.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype("float32")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    faiss.write_index(index, INDEX_FILE)
    with open(CHUNKS_FILE, "wb") as f:
        pickle.dump(chunks, f)
    with open(BM25_FILE, "wb") as f:
        pickle.dump(bm25, f)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(file_signature(TEXT_FILE), f, ensure_ascii=False, indent=2)

    log(f"인덱스 생성 완료: {len(chunks)}개 조각")


def load_resources():
    build_index(force=False)
    index = faiss.read_index(INDEX_FILE)
    with open(CHUNKS_FILE, "rb") as f:
        chunks = pickle.load(f)
    with open(BM25_FILE, "rb") as f:
        bm25 = pickle.load(f)
    embedder = load_embedder()
    return index, chunks, bm25, embedder


def minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if math.isclose(lo, hi):
        return [1.0 if hi > 0 else 0.0 for _ in values]
    return [(v - lo) / (hi - lo) for v in values]


def search_rag_evidence(query: str, top_k: int = TOP_K) -> list[SearchHit]:
    index, chunks, bm25, embedder = load_resources()

    bm25_raw = list(map(float, bm25.get_scores(tokenize(query))))
    query_vector = embedder.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
    vector_scores, vector_indices = index.search(query_vector, min(max(top_k * 4, top_k), len(chunks)))

    candidate_ids = set(np.argsort(bm25_raw)[-top_k * 4:].tolist())
    candidate_ids.update(int(i) for i in vector_indices[0] if i >= 0)

    candidate_ids_list = sorted(candidate_ids)
    bm25_values = [bm25_raw[i] for i in candidate_ids_list]

    vector_map = {int(i): float(s) for i, s in zip(vector_indices[0], vector_scores[0]) if i >= 0}
    vector_values = [vector_map.get(i, 0.0) for i in candidate_ids_list]

    bm25_norm = minmax(bm25_values)
    vector_norm = minmax(vector_values)

    hits: list[SearchHit] = []
    for pos, chunk_id in enumerate(candidate_ids_list):
        hybrid = (bm25_norm[pos] * 0.5) + (vector_norm[pos] * 0.5)
        hits.append(SearchHit(
            chunk_id=chunk_id,
            bm25_score=bm25_norm[pos],
            vector_score=vector_norm[pos],
            hybrid_score=hybrid,
            text=chunks[chunk_id],
        ))

    hits.sort(key=lambda h: h.hybrid_score, reverse=True)
    return hits[:top_k]


def parse_question_block(text: str) -> tuple[str, list[str]]:
    text = normalize_text(text)
    pattern = r"(?m)^\s*(\d{1,2})\s*[\.|\)|、]\s*(.+?)(?=\n\s*\d{1,2}\s*[\.|\)|、]\s*|\Z)"
    matches = list(re.finditer(pattern, text, flags=re.DOTALL))
    if len(matches) < 2:
        raise ValueError("보기 형식을 찾지 못했습니다. 예: 1. 보기내용 / 2. 보기내용 형태로 입력하세요.")

    question = text[:matches[0].start()].strip()
    choices = [re.sub(r"\s+", " ", m.group(2)).strip() for m in matches]
    if not question:
        raise ValueError("문제 내용을 찾지 못했습니다. 보기 위에 문제 내용을 입력하세요.")
    return question, choices


def score_choice_by_rag(question: str, choice: str) -> dict[str, Any]:
    # 문제+보기 조합으로 근거 검색. 보기별로 RAG 검색 결과가 달라져 점수화가 더 안정적입니다.
    query = f"{question}\n정답 후보: {choice}"
    hits = search_rag_evidence(query, top_k=TOP_K)

    if not hits:
        return {"bm25": 0.0, "vector": 0.0, "rag": 0.0, "evidence": []}

    # 상위 근거에 더 큰 가중치를 둡니다.
    weights = [1.0 / (rank + 1) for rank in range(len(hits))]
    weight_sum = sum(weights)
    bm25_score = sum(hit.bm25_score * w for hit, w in zip(hits, weights)) / weight_sum
    vector_score = sum(hit.vector_score * w for hit, w in zip(hits, weights)) / weight_sum
    rag_score = (bm25_score * 0.5) + (vector_score * 0.5)

    return {
        "bm25": bm25_score,
        "vector": vector_score,
        "rag": rag_score,
        "evidence": hits[:3],
    }


def call_ollama_scores(question: str, choices: list[str], evidence_text: str) -> dict[int, float]:
    choices_text = "\n".join(f"{i + 1}. {choice}" for i, choice in enumerate(choices))
    prompt = f"""
당신은 OCR 문서 기반 객관식 문제 채점기입니다.
[문서 근거] 안에서만 판단해서 각 보기의 정답 가능성을 0~100 정수 점수로 매기세요.
설명하지 말고 JSON만 출력하세요.

[문서 근거]
{evidence_text}

[문제]
{question}

[보기]
{choices_text}

[출력 JSON]
{{"scores": {{"1": 0, "2": 0, "3": 0, "4": 0}}}}
""".strip()
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "top_p": 0.8, "num_ctx": 4096},
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(f"Ollama 호출 실패: {response.status_code} {response.text}")
    text = response.json().get("response", "")
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end + 1])
            return {int(k): float(v) for k, v in data.get("scores", {}).items()}
        except Exception:
            pass
    guessed = {}
    for num, score in re.findall(r"[\"']?(\d+)[\"']?\s*[:=]\s*(\d+)", text):
        guessed[int(num)] = float(score)
    return guessed


def normalize_to_percent(scores: list[tuple[int, float]]) -> list[tuple[int, int]]:
    cleaned = [(num, max(0.0, score)) for num, score in scores]
    total = sum(score for _, score in cleaned)
    if total <= 0:
        even = int(100 / len(cleaned)) if cleaned else 0
        return [(num, even) for num, _ in cleaned]
    percents = [(num, int(round(score / total * 100))) for num, score in cleaned]
    diff = 100 - sum(percent for _, percent in percents)
    max_idx = max(range(len(percents)), key=lambda i: percents[i][1])
    num, percent = percents[max_idx]
    percents[max_idx] = (num, percent + diff)
    percents.sort(key=lambda x: x[1], reverse=True)
    return percents


def answer_question_block(block_text: str, use_llm: bool = USE_LLM, show_debug: bool = False) -> str:
    question, choices = parse_question_block(block_text)

    log("보기별 BM25+벡터 RAG 점수 계산 중")
    choice_rows = []
    all_evidence_texts = []
    for idx, choice in enumerate(choices, start=1):
        scored = score_choice_by_rag(question, choice)
        choice_rows.append({"num": idx, "choice": choice, **scored})
        for hit in scored["evidence"]:
            all_evidence_texts.append(f"[보기 {idx} 근거 / chunk {hit.chunk_id}]\n{hit.text}")

    bm25_norm = minmax([row["bm25"] for row in choice_rows])
    vector_norm = minmax([row["vector"] for row in choice_rows])
    rag_norm = minmax([row["rag"] for row in choice_rows])

    llm_norm = [0.0 for _ in choice_rows]
    active_weights = {"bm25": WEIGHT_BM25, "vector": WEIGHT_VECTOR, "llm": 0.0}

    if use_llm:
        log(f"Ollama LLM 보정 점수 계산 중: {LLM_MODEL}")
        evidence_text = "\n\n".join(dict.fromkeys(all_evidence_texts))[:9000]
        try:
            llm_scores = call_ollama_scores(question, choices, evidence_text)
            llm_raw = [llm_scores.get(row["num"], 0.0) for row in choice_rows]
            llm_norm = minmax(llm_raw)
            active_weights = {"bm25": WEIGHT_BM25, "vector": WEIGHT_VECTOR, "llm": WEIGHT_LLM}
        except Exception as exc:
            log(f"LLM 보정 실패. BM25+벡터검색만 사용합니다: {exc}")

    weight_total = sum(active_weights.values()) or 1.0
    final_scores: list[tuple[int, float]] = []
    for pos, row in enumerate(choice_rows):
        final = (
            bm25_norm[pos] * active_weights["bm25"]
            + vector_norm[pos] * active_weights["vector"]
            + llm_norm[pos] * active_weights["llm"]
        ) / weight_total
        # 모든 보기가 거의 0점일 때도 근거검색 순위를 반영하기 위한 보조값입니다.
        final += rag_norm[pos] * 0.0001
        final_scores.append((row["num"], final))

    ranked = normalize_to_percent(final_scores)
    answer_line = "답 : " + ", ".join(f"{num}번({percent}%)" for num, percent in ranked[:2])

    if not show_debug:
        return answer_line

    debug_lines = [answer_line, "", "[보기별 점수]"]
    percent_map = dict(ranked)
    for pos, row in enumerate(choice_rows):
        debug_lines.append(
            f"{row['num']}번 | 확률 {percent_map.get(row['num'], 0)}% | "
            f"BM25 {bm25_norm[pos]:.3f} | VECTOR {vector_norm[pos]:.3f} | LLM {llm_norm[pos]:.3f}"
        )
        if row["evidence"]:
            first = row["evidence"][0]
            snippet = re.sub(r"\s+", " ", first.text)[:160]
            debug_lines.append(f"  근거: {snippet}...")
    return "\n".join(debug_lines)



QUIZ_QUESTIONS_FILE = "generated_quiz_questions.txt"
QUIZ_ANSWERS_FILE = "generated_quiz_answers.txt"
QUIZ_WITH_ANSWERS_FILE = "generated_quiz_with_answers.txt"


def split_sentences_for_quiz(text: str) -> list[str]:
    """result.txt에서 문제 보기로 쓰기 좋은 문장을 추출합니다."""
    text = normalize_text(text)
    # OCR 잡음과 페이지 번호 같은 짧은 줄을 줄입니다.
    raw_parts = re.split(r"(?<=[.!?。！？다요함임음됨됨다])\s+|\n+", text)
    sentences: list[str] = []
    seen = set()

    for part in raw_parts:
        sentence = re.sub(r"\s+", " ", part).strip()
        sentence = re.sub(r"^[\-•*\d\s.\)]+", "", sentence).strip()
        if not (25 <= len(sentence) <= 180):
            continue
        # 보기로 부적합한 목차/잡음성 문장 제외
        if len(re.findall(r"[가-힣]", sentence)) < 10:
            continue
        if re.search(r"^(표|그림|페이지|page|chapter|목차)\b", sentence, re.IGNORECASE):
            continue
        key = sentence.lower()
        if key in seen:
            continue
        seen.add(key)
        sentences.append(sentence)

    return sentences


def make_question_text(correct_sentence: str) -> str:
    """정답 문장을 기반으로 범용 객관식 문제 문장을 만듭니다."""
    subject = correct_sentence
    subject = re.sub(r"[.。]$", "", subject).strip()
    if len(subject) > 70:
        subject = subject[:70].rstrip() + "..."
    templates = [
        f"다음 내용과 관련하여 옳은 설명은 무엇인가? ({subject})",
        f"문서의 설명으로 가장 적절한 것은 무엇인가?",
        f"다음 주제에 대한 설명으로 옳은 것은 무엇인가? ({subject})",
        f"문서 내용 기준으로 맞는 설명은 무엇인가?",
    ]
    return random.choice(templates)



def clean_korean_sentence(text: str, max_len: int = 160) -> str:
    """OCR 잡음을 줄이고 보기로 읽기 쉬운 한글 문장 형태로 정리합니다."""
    text = normalize_text(text)
    text = re.sub(r"^[\-•*\d\s.\)]+", "", text).strip()
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[|_]{2,}", " ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rstrip() + "..."
    if text and not re.search(r"[.!?다요함임음됨]$", text):
        text += "."
    return text


def call_ollama_quiz(context: str, q_no: int, model_name: str = LLM_MODEL) -> dict[str, Any]:
    """Ollama 로컬 LLM으로 자연스러운 4지선다 문제 1개를 생성합니다."""
    prompt = f"""
당신은 한국어 객관식 시험문제 출제자입니다.
아래 [문서 내용]만 근거로 자연스러운 한국어 4지선다 문제 1개를 만드세요.

규칙:
1. 문제는 반드시 한국어 자연문장으로 작성하세요.
2. 보기는 4개이며, 1개만 정답이어야 합니다.
3. 보기는 원문을 그대로 잘라 붙이지 말고 시험 보기처럼 부드럽게 다듬으세요.
4. 문서에 없는 내용을 정답으로 만들지 마세요.
5. 설명하지 말고 JSON만 출력하세요.
6. JSON 형식은 정확히 아래 형식을 따르세요.

[문서 내용]
{context[:3500]}

[출력 JSON]
{{
  "question": "문제 내용",
  "choices": ["보기1", "보기2", "보기3", "보기4"],
  "answer": 1
}}
""".strip()
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.35, "top_p": 0.8, "num_ctx": 4096},
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=180)
    if response.status_code != 200:
        raise RuntimeError(f"Ollama 호출 실패: {response.status_code} {response.text}")
    text = response.json().get("response", "")
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError(f"LLM 응답에서 JSON을 찾지 못했습니다: {text[:300]}")
    data = json.loads(text[start:end + 1])
    question = clean_korean_sentence(str(data.get("question", "")), max_len=140)
    choices = [clean_korean_sentence(str(c), max_len=140) for c in data.get("choices", [])]
    answer = int(data.get("answer", 0))
    if not question or len(choices) != 4 or answer not in {1, 2, 3, 4}:
        raise ValueError(f"LLM 문제 형식이 올바르지 않습니다: {data}")
    return {"question": question, "choices": choices, "answer": answer}


def fallback_quiz_from_sentence(correct_idx: int, sentences: list[str], vectors: np.ndarray) -> dict[str, Any] | None:
    """LLM 없이도 자연스러운 문장에 가깝게 4지선다 문제를 만듭니다."""
    correct = clean_korean_sentence(sentences[correct_idx])
    distractors = pick_distractors_by_vector(correct_idx, sentences, vectors, count=3)
    if len(distractors) < 3:
        return None
    choices = [correct] + [clean_korean_sentence(d) for d in distractors[:3]]
    random.shuffle(choices)
    return {
        "question": "문서 내용으로 보아 가장 적절한 설명은 무엇인가?",
        "choices": choices,
        "answer": choices.index(correct) + 1,
    }

def pick_distractors_by_vector(correct_idx: int, sentences: list[str], vectors: np.ndarray, count: int = 3) -> list[str]:
    """정답과 의미가 어느 정도 가까운 문장을 오답으로 골라 난이도를 높입니다."""
    if len(sentences) <= 1:
        return []

    sims = np.dot(vectors, vectors[correct_idx])
    order = np.argsort(-sims)
    distractors: list[str] = []
    correct = sentences[correct_idx]

    for idx in order:
        idx = int(idx)
        if idx == correct_idx:
            continue
        candidate = sentences[idx]
        if candidate == correct:
            continue
        # 너무 비슷하면 사실상 같은 보기일 수 있어 제외합니다.
        if float(sims[idx]) > 0.96:
            continue
        if len(set(tokenize(candidate)) & set(tokenize(correct))) < 2:
            # 완전히 무관한 오답은 뒤로 미룹니다.
            continue
        distractors.append(candidate)
        if len(distractors) >= count:
            return distractors

    # 부족하면 랜덤 문장으로 채웁니다.
    pool = [s for i, s in enumerate(sentences) if i != correct_idx and s not in distractors]
    random.shuffle(pool)
    for candidate in pool:
        distractors.append(candidate)
        if len(distractors) >= count:
            break
    return distractors


def generate_random_quiz(
    count: int = 10,
    seed: int | None = None,
    use_llm: bool = False,
    quiz_model: str = LLM_MODEL,
) -> tuple[str, str, str]:
    """result.txt 기준 랜덤 객관식 문제를 생성하고 파일로 저장합니다.

    use_llm=True이면 Ollama 로컬 LLM으로 문제/보기를 자연스러운 한글 문장으로 생성합니다.
    LLM 호출 실패 또는 응답 형식 오류 시 BM25+벡터 기반의 비LLM 문제 생성 방식으로 자동 대체됩니다.
    """
    if seed is not None:
        random.seed(seed)

    text = read_text(TEXT_FILE)
    sentences = split_sentences_for_quiz(text)
    if len(sentences) < 8:
        raise ValueError("문제를 만들 문장이 부족합니다. result.txt 텍스트 양을 늘리거나 OCR 결과를 확인하세요.")

    embedder = load_embedder()
    log(f"문제 후보 문장 {len(sentences)}개 임베딩 생성 중")
    vectors = embedder.encode(
        sentences,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    ).astype("float32")

    total = min(count, len(sentences))
    chosen_indices = random.sample(range(len(sentences)), total)

    question_lines: list[str] = []
    answer_lines: list[str] = []
    with_answer_lines: list[str] = []

    for q_no, correct_idx in enumerate(chosen_indices, start=1):
        quiz_data = None

        if use_llm:
            hits = search_rag_evidence(sentences[correct_idx], top_k=5)
            context = "\n\n".join(hit.text for hit in hits)
            if not context.strip():
                context = sentences[correct_idx]
            try:
                log(f"문제{q_no}번 LLM 생성 중: {quiz_model}")
                quiz_data = call_ollama_quiz(context=context, q_no=q_no, model_name=quiz_model)
            except Exception as exc:
                log(f"문제{q_no}번 LLM 생성 실패. 비LLM 방식으로 대체합니다: {exc}")

        if quiz_data is None:
            quiz_data = fallback_quiz_from_sentence(correct_idx, sentences, vectors)

        if quiz_data is None:
            continue

        question = clean_korean_sentence(quiz_data["question"], max_len=140)
        choices = [clean_korean_sentence(choice, max_len=140) for choice in quiz_data["choices"]]
        answer_no = int(quiz_data["answer"])

        block = [f"문제{q_no}번. {question}"]
        for i, choice in enumerate(choices, start=1):
            block.append(f"{i}. {choice}")
        block_text = "\n".join(block)

        question_lines.append(block_text)
        answer_lines.append(f"문제{q_no}번 정답 : {answer_no}번")
        with_answer_lines.append(block_text + f"\n정답 : {answer_no}번")

    questions_text = "\n\n".join(question_lines)
    answers_text = "\n".join(answer_lines)
    with_answers_text = "\n\n".join(with_answer_lines)

    with open(QUIZ_QUESTIONS_FILE, "w", encoding="utf-8") as f:
        f.write(questions_text)
    with open(QUIZ_ANSWERS_FILE, "w", encoding="utf-8") as f:
        f.write(answers_text)
    with open(QUIZ_WITH_ANSWERS_FILE, "w", encoding="utf-8") as f:
        f.write(with_answers_text)

    return questions_text, answers_text, with_answers_text


def read_multiline_question() -> str:
    print("\n문제와 보기를 붙여넣으세요. 입력 완료 후 빈 줄을 한 번 입력하세요.")
    print("종료하려면 exit 입력")
    lines: list[str] = []
    while True:
        line = input()
        if not lines and line.strip().lower() in {"exit", "quit", "q"}:
            return "exit"
        if line.strip() == "" and lines:
            break
        if line.strip() == "" and not lines:
            continue
        lines.append(line)
    return "\n".join(lines)


def interactive_mode(use_llm: bool, show_debug: bool) -> None:
    log("OCR 문서 기반 객관식 QA 프로그램 시작")
    build_index(force=False)
    while True:
        block = read_multiline_question()
        if block.lower() == "exit":
            log("프로그램 종료")
            break
        try:
            print("\n" + "=" * 60)
            print(answer_question_block(block, use_llm=use_llm, show_debug=show_debug))
            print("=" * 60)
        except Exception as exc:
            print(f"오류: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR result.txt 기반 BM25+벡터검색 객관식 QA + 랜덤 문제 생성")
    parser.add_argument("--rebuild", action="store_true", help="인덱스를 강제로 다시 생성합니다.")
    parser.add_argument("--llm", action="store_true", help="Ollama 로컬 LLM 보정 점수를 추가합니다.")
    parser.add_argument("--debug", action="store_true", help="보기별 점수와 근거를 함께 출력합니다.")
    parser.add_argument("--quiz", type=int, default=0, help="result.txt 기준 랜덤 객관식 문제를 N개 생성합니다. 예: --quiz 10")
    parser.add_argument("--quiz-llm", action="store_true", help="Ollama 로컬 LLM으로 자연스러운 한글 문제/보기를 생성합니다.")
    parser.add_argument("--quiz-model", default=LLM_MODEL, help="문제 생성에 사용할 Ollama 모델명입니다. 예: qwen:0.5b, llama3:8b")
    parser.add_argument("--seed", type=int, default=None, help="문제 랜덤 생성 시드입니다. 같은 문제를 재생성할 때 사용합니다.")
    args = parser.parse_args()

    if args.rebuild:
        build_index(force=True)

    if args.quiz > 0:
        log(f"랜덤 객관식 문제 {args.quiz}개 생성 시작")
        questions, answers, _ = generate_random_quiz(
            count=args.quiz,
            seed=args.seed,
            use_llm=args.quiz_llm,
            quiz_model=args.quiz_model,
        )
        print("\n" + questions)
        print("\n" + "=" * 60)
        print(f"문제 파일: {QUIZ_QUESTIONS_FILE}")
        print(f"정답 파일: {QUIZ_ANSWERS_FILE}")
        print(f"정답 포함 파일: {QUIZ_WITH_ANSWERS_FILE}")
        print("=" * 60)
        return

    interactive_mode(use_llm=args.llm, show_debug=args.debug)

if __name__ == "__main__":
    main()
