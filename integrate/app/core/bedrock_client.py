import json
import time

import boto3
from botocore.config import Config

from app.core.config import AWS_REGION, MODEL_ID, BEDROCK_READ_TIMEOUT
from app.core.logger import log_info
from app.core.token_tracker import add_usage


bedrock_client = boto3.client(
    'bedrock-runtime',
    region_name=AWS_REGION,
    config=Config(read_timeout=BEDROCK_READ_TIMEOUT, connect_timeout=30, retries={'max_attempts': 3, 'mode': 'standard'}),
)


def invoke_bedrock(system_prompt: str, user_prompt: str, max_tokens: int = 4000, retry_count: int = 3) -> str:
    # JSON 생성/복구 응답은 중간 절단 시 파싱 오류가 발생할 수 있으므로
    # process.json max_token으로 프롬프트/응답 본문을 강제 절단하지 않습니다.
    # max_token은 최종 파일 산출물에 텍스트를 기록하는 output 단계에서만 적용합니다.
    effective_max_tokens = int(max_tokens or 4000)
    request_body = {
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': effective_max_tokens,
        'temperature': 0,
        'system': system_prompt,
        'messages': [{'role': 'user', 'content': user_prompt}],
    }
    last_error = None
    for attempt in range(1, retry_count + 1):
        try:
            response = bedrock_client.invoke_model(modelId=MODEL_ID, body=json.dumps(request_body))
            response_body = json.loads(response['body'].read().decode('utf-8'))
            usage = response_body.get('usage', {})
            add_usage(input_tokens=usage.get('input_tokens', 0), output_tokens=usage.get('output_tokens', 0))
            return response_body['content'][0]['text']
        except Exception as e:
            last_error = e
            log_info(f'Bedrock 호출 실패 {attempt}/{retry_count}: {e}')
            time.sleep(2 * attempt)
    raise last_error
