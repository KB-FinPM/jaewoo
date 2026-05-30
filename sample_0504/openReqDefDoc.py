import boto3
import json

from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama.chat_models import ChatOllama
from datetime import datetime
 

# 1. 문서 로드(구축요건정의서)
loader = Docx2txtLoader("./탬플릿/01.구축요건정의서/KB스타뱅킹전용플레임워크구축.docx")
documents = loader.load()
 
# 2. 텍스트 분할
splitter = RecursiveCharacterTextSplitter (
    chunk_size = 1000,
    chunk_overlap = 100
)
 
split_docs = splitter.split_documents(documents)
 
now = datetime.now(). strftime("%Y-%m-%d %H:%M:%S")
print(f"[{now}] 분할된 문서 개수: {len(split_docs)} ")

# 3. bedrock client 설정
account_id = "956723945403"
model_id = "arn:aws:bedrock:ap-northeast-2:956723945403:inference-profile/global.anthropic.claude-sonnet-4-6"

client = boto3.client("bedrock-runtime", region_name="ap-northeast-2")

# 토큰 사용량 요약
token_summaries = [ 0 , 0 ]   # [입력 토큰 총합, 출력 토큰 총합]







# 4. 분석 함수
def analyze_documents(docs):
    chunk_summaries = []
   
    # 각 chunk 분석
    for i , doc in enumerate(docs):

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": f"""{doc.page_content}"""
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
        print(f"[{now}] [ {i + 1} / {len(docs)} ] 분석 완료")

        usage = response_body.get("usage", {})
        token_summaries[0] += usage.get("input_tokens", 0)
        token_summaries[1] += usage.get("output_tokens", 0)

    return chunk_summaries

# 5. 실행
chunk_results = analyze_documents(split_docs)

# 6. 통합 분석
combined_summary = "\n".join(chunk_results)

final_request_body = {
	"anthropic_version": "bedrock-2023-05-31",
	"max_tokens": 1000,
	"messages": [
		{
			"role": "user",
			"content": f"""
				당신은 프로젝트 매니저(PM)입니다.
				아래는 문서의 여러 부분을 분석한 결과입니다.
				이들을 종합하여 최종 정리하세요.

				분석 결과:
				{combined_summary}

				최종 정리:
				1. 주요 내용 요약
				2. 일정 관련 내용
				3. 리스크 요소
				4. 실행해야 할 Action Item
				"""
		}
	]
}

final_response = client.invoke_model(
    modelId=model_id,
    body=json.dumps(final_request_body)
)
final_response_body = json.loads(final_response["body"].read())

# 토큰 사용량 업데이트
usage = final_response_body.get("usage", {})
token_summaries[0] += usage.get("input_tokens", 0)
token_summaries[1] += usage.get("output_tokens", 0) 

# 7. 최종 결과 출력
print(" \n ===== 최종 분석 결과 =====")
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"[{now}] {final_response_body['content'][0]['text']} ")
print(f" \n 입력 토큰, 출력 토큰, 토큰 합계 : {token_summaries [ 0 ]} / {token_summaries [ 1 ]} / {token_summaries [ 0 ] + token_summaries [ 1 ]} ")