import os
import json
import boto3

from dotenv import load_dotenv
from datetime import datetime

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter
) 

def analyze_text_chunks(results):

    # 3. bedrock client 설정
    load_dotenv()
    model_id = os.getenv("MODEL_ID")
    client = boto3.client("bedrock-runtime", region_name="ap-northeast-2")

    # 토큰 사용량 요약
    token_summaries = [ 0 , 0 ]   # [입력 토큰 총합, 출력 토큰 총합]

    # =====================================
    # results -> 문자열 변환
    # =====================================

    full_text = ""

    for item in results:

        # Heading
        if item["type"] == "heading":

            full_text += f"\n[제목]\n{item['text']}\n"

        # 본문
        elif item["type"] == "paragraph":

            full_text += f"\n{item['text']}\n"

        # 표
        elif item["type"] == "table":

            table_text = json.dumps(
                item["data"],
                ensure_ascii=False
            )

            full_text += f"\n[표]\n{table_text}\n"

    print("입력 추출값 시작 =====================================")
    print(full_text);            
    print("입력 추출값 종료 =====================================")

    # =====================================
    # Chunk 분할
    # =====================================

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )

    chunks = splitter.split_text(full_text)

    # =====================================
    # 결과 분석
    # =====================================

    chunk_summaries = []
   
    # 각 chunk 분석
    for i , doc in enumerate(chunks):

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": f"""{doc.strip()}"""
                }
            ]
        }
 
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        response_body = json.loads(response["body"].read())

        chunk_summaries.append(response_body["content"][0]["text"])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] [ {i + 1} / {len(chunks)} ] 분석 완료")

        usage = response_body.get("usage", {})
        token_summaries[0] += usage.get("input_tokens", 0)
        token_summaries[1] += usage.get("output_tokens", 0)

    print(f" \n Text_Analyzer - 입력 토큰, 출력 토큰, 토큰 합계 : {token_summaries [ 0 ]} / {token_summaries [ 1 ]} / {token_summaries [ 0 ] + token_summaries [ 1 ]} ")
    return chunk_summaries