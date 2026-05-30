import boto3
import json

client = boto3.client("bedrock-runtime", region_name="ap-northeast-2")  

# 본인 account_id 설정 필요. 
# 로컬에 accesskey, seckey, bedrock api key 설정 필요 
account_id = "956723945403"
model_id = "arn:aws:bedrock:ap-northeast-2:956723945403:inference-profile/global.anthropic.claude-sonnet-4-6"


request_body = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 1000,
    "messages": [
        {
            "role": "user",
            "content": "PM 산출물 종류는 어떤것이 있나요?"
        }
    ]
}

try:
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body)
    )
    response_body = json.loads(response["body"].read())
    print(response_body["content"][0]["text"])
except Exception as e:
    print(f"Bedrock API 오류: {e}")