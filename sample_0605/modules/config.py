import os
from dotenv import load_dotenv

load_dotenv(override=False)

AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_VERIFY_SSL = os.getenv('AWS_VERIFY_SSL', 'true').lower() != 'false'
AWS_CA_BUNDLE = os.getenv('AWS_CA_BUNDLE')

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
S3_STORAGE_BACKEND = os.getenv('S3_STORAGE_BACKEND', 's3')
S3_UPLOAD_PREFIX = os.getenv('S3_UPLOAD_PREFIX', 'storage/upload_files')
S3_TEMPLATE_PREFIX = os.getenv('S3_TEMPLATE_PREFIX', 'storage/template_files')
S3_GENERATED_PREFIX = os.getenv('S3_GENERATED_PREFIX', 'storage/generated_files')

DATABASE_URL = os.getenv('DATABASE_URL')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'BAAI/bge-m3')
CHUNK_MAX_CHARS = int(os.getenv('CHUNK_MAX_CHARS', '1200'))
CHUNK_OVERLAP_CHARS = int(os.getenv('CHUNK_OVERLAP_CHARS', '150'))
WBS_BATCH_SIZE = int(os.getenv('WBS_BATCH_SIZE', '10'))
SCREEN_BATCH_SIZE = int(os.getenv('SCREEN_BATCH_SIZE', '10'))
BEDROCK_READ_TIMEOUT = int(os.getenv('BEDROCK_READ_TIMEOUT', '300'))
RECREATE_COLLECTION = os.getenv('RECREATE_COLLECTION', 'false').lower() == 'true'

PROJECT_NAME = os.getenv('PROJECT_NAME', '프로젝트명')
AUTHOR_NAME = os.getenv('AUTHOR_NAME', '작성자')

REQUIREMENT_TEMPLATE_PATH = os.getenv('REQUIREMENT_TEMPLATE_PATH', 'template/탬플릿_요구사항명세서.xlsx')
WBS_TEMPLATE_PATH = os.getenv('WBS_TEMPLATE_PATH', 'template/탬플릿_WBS.xlsx')
SCREEN_TEMPLATE_PATH = os.getenv('SCREEN_TEMPLATE_PATH', 'template/탬플릿_화면설계서.pptx')
OUTPUT_MAPPER_PATH = os.getenv('OUTPUT_MAPPER_PATH', 'template/output_mapper.json')

if not BEDROCK_MODEL_ID:
    raise ValueError('BEDROCK_MODEL_ID가 .env에 설정되어 있지 않습니다.')
