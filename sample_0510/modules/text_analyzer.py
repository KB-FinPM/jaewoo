import os
import json
import re
import boto3

from datetime import datetime
from dotenv import load_dotenv
from modules.excel_handler import append_to_excel, create_workbook

from langchain_text_splitters import RecursiveCharacterTextSplitter


def is_separator_row(line: str) -> bool:
    return bool(re.fullmatch(r"[\s|:\-]+", line))


def analyze_text_chunks(results: list[dict]) -> tuple[str, str]:
    load_dotenv()
    model_id = os.getenv("MODEL_ID")
    client = boto3.client("bedrock-runtime", region_name="ap-northeast-2")

    token_summaries = [0, 0]
    text_blocks: list[str] = []

    for item in results:
        if item["type"] == "heading":
            text_blocks.append(f"[제목]\n{item['text']}")
        elif item["type"] == "paragraph":
            text_blocks.append(item["text"])
        elif item["type"] == "table":
            text_blocks.append(json.dumps(item["data"], ensure_ascii=False))

    full_text = "\n\n".join(text_blocks).strip()
    print("입력 추출값 시작 =====================================")
    print(full_text)
    print("입력 추출값 종료 =====================================")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(full_text)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    output_dir = "./results"
    os.makedirs(output_dir, exist_ok=True)
    excel_path = os.path.join(output_dir, f"analysis_{now.replace(':', '').replace('-', '').replace(' ', '_')}.xlsx")
    create_workbook(excel_path)
    print(f"\n[{now}] 엑셀 파일 생성: {excel_path}")

    chunk_summaries: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": f"""
                        당신은 프로젝트 매니저(PM)입니다.
                        아래는 문서의 일부 내용입니다.
                        이 내용을 요구사항 명세서 형식으로 정리해주세요.

                        출력 형식:
                        - 컬럼: 업무, 구분, 요구사항ID, 요구사항명, 기능/비기능 요구사항, 비고
                        - Markdown 또는 CSV 표 형태로 작성
                        - 각 요구사항은 한 줄에 하나씩 작성

                        문서 내용:
                        {chunk.strip()}
                        """
                }
            ],
        }

        response = client.invoke_model(modelId=model_id, body=json.dumps(request_body))
        response_body = json.loads(response["body"].read())

        chunk_summary = response_body["content"][0]["text"].strip()
        chunk_summaries.append(chunk_summary)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] [ {index} / {len(chunks)} ] 분석 완료")

        usage = response_body.get("usage", {})
        token_summaries[0] += usage.get("input_tokens", 0)
        token_summaries[1] += usage.get("output_tokens", 0)

        append_to_excel(chunk_summary, excel_path, is_final=False)
        print(f"[{now}] 청크 분석 결과 엑셀에 추가됨")

    print(
        f"\nText_Analyzer - 입력 토큰: {token_summaries[0]}, 출력 토큰: {token_summaries[1]}, 합계: {sum(token_summaries)}"
    )

    final_text = "\n\n".join(chunk_summaries)
    return final_text, excel_path