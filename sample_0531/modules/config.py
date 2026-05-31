import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-2')
MODEL_ID = os.getenv('MODEL_ID')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
QDRANT_COLLECTION = os.getenv('QDRANT_COLLECTION', 'pm_requirement_atoms')
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

if not MODEL_ID:
    raise ValueError('MODEL_ID가 .env에 설정되어 있지 않습니다.')
