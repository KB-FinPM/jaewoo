import json
import time

import boto3
from botocore.config import Config

from modules.config import AWS_REGION, MODEL_ID, BEDROCK_READ_TIMEOUT
from modules.logger_utils import log_info
from modules.token_tracker import add_usage


bedrock_client = boto3.client(
    'bedrock-runtime',
    region_name=AWS_REGION,
    config=Config(read_timeout=BEDROCK_READ_TIMEOUT, connect_timeout=30, retries={'max_attempts': 3, 'mode': 'standard'}),
)


def invoke_bedrock(system_prompt: str, user_prompt: str, max_tokens: int = 4000, retry_count: int = 3) -> str:
    request_body = {
        'anthropic_version': 'bedrock-2023-05-31',
        'max_tokens': max_tokens,
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
