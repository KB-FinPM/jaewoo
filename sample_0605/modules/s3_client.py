import os
import tempfile
from pathlib import Path
from typing import List, Optional

import boto3
from botocore.config import Config
from dotenv import load_dotenv

load_dotenv(override=True)


def get_s3_client():
    """S3 클라이언트를 생성합니다."""
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'ap-northeast-2')
    aws_verify_ssl = os.getenv('AWS_VERIFY_SSL', 'true').lower() != 'false'
    aws_ca_bundle = os.getenv('AWS_CA_BUNDLE') or None

    session_kwargs = {
        'region_name': aws_region,
        'config': Config(retries={'max_attempts': 3, 'mode': 'standard'}),
        'verify': aws_verify_ssl,
    }
    if aws_ca_bundle:
        session_kwargs['verify'] = aws_ca_bundle

    if aws_access_key_id and aws_secret_access_key:
        session_kwargs['aws_access_key_id'] = aws_access_key_id
        session_kwargs['aws_secret_access_key'] = aws_secret_access_key

    return boto3.client('s3', **session_kwargs)


def verify_bucket_access(bucket_name: Optional[str] = None) -> bool:
    """버킷 접근 가능 여부를 확인합니다."""
    bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
    if not bucket_name:
        raise ValueError('S3_BUCKET_NAME이 .env에 설정되어 있지 않습니다.')

    client = get_s3_client()
    client.head_bucket(Bucket=bucket_name)
    return True


def upload_file(local_path: str, key: str, bucket_name: Optional[str] = None) -> str:
    """로컬 파일을 S3에 업로드합니다."""
    bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
    if not bucket_name:
        raise ValueError('S3_BUCKET_NAME이 .env에 설정되어 있지 않습니다.')

    client = get_s3_client()
    client.upload_file(local_path, bucket_name, key)
    return f's3://{bucket_name}/{key}'


def generate_key(prefix: str, filename: str) -> str:
    """S3 key를 생성합니다."""
    return f'{prefix.rstrip("/")}/{filename}'.replace('//', '/')


def is_s3_uri(path: Optional[str]) -> bool:
    return isinstance(path, str) and path.startswith('s3://')


def local_to_s3_key(local_path: str, prefix: str) -> Optional[str]:
    """로컬 경로를 S3 prefix 기준 키로 변환합니다."""
    if not local_path:
        return None
    candidate = Path(local_path)
    if candidate.is_absolute():
        try:
            candidate = candidate.relative_to(Path.cwd())
        except ValueError:
            pass

    parts = candidate.parts
    if len(parts) >= 2 and parts[0] in ('input', 'template'):
        relative = Path(*parts[1:]).as_posix()
        return f"{prefix.rstrip('/')}/{relative}".replace('//', '/')
    return None


def list_s3_keys(prefix: str, bucket_name: Optional[str] = None) -> List[str]:
    """S3 prefix 아래 파일 목록을 반환합니다."""
    bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
    if not bucket_name:
        return []

    client = get_s3_client()
    paginator = client.get_paginator('list_objects_v2')
    keys = []
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix.rstrip('/') + '/'):
        for item in page.get('Contents', []):
            key = item.get('Key')
            if key:
                keys.append(key)
    return keys


def download_file_from_s3(key: str, bucket_name: Optional[str] = None, cache_dir: Optional[str] = None) -> str:
    """S3 파일을 캐시 디렉터리로 다운로드합니다."""
    bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
    if not bucket_name:
        raise ValueError('S3_BUCKET_NAME이 .env에 설정되어 있지 않습니다.')

    target_dir = Path(cache_dir) if cache_dir else Path(tempfile.gettempdir()) / 'pm-agent-s3-cache'
    target_file = target_dir / key.lstrip('/')
    target_file.parent.mkdir(parents=True, exist_ok=True)

    client = get_s3_client()
    client.download_file(bucket_name, key, str(target_file))
    return str(target_file)


def ensure_local_path(path: str, bucket_name: Optional[str] = None, cache_dir: Optional[str] = None) -> str:
    """S3 경로 또는 로컬 경로를 로컬 캐시 경로로 보장합니다."""
    if is_s3_uri(path):
        return download_file_from_s3(path.replace('s3://', '').split('/', 1)[1], bucket_name=bucket_name, cache_dir=cache_dir)

    local_path = Path(path)
    if local_path.exists():
        return str(local_path)

    bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
    if not bucket_name or os.getenv('S3_STORAGE_BACKEND', 's3') != 's3':
        return str(local_path)

    prefix = os.getenv('S3_TEMPLATE_PREFIX') if 'template/' in path else os.getenv('S3_UPLOAD_PREFIX')
    if prefix and 'template/' in path:
        s3_key = local_to_s3_key(path, prefix)
    elif prefix and 'input/' in path:
        s3_key = local_to_s3_key(path, prefix)
    else:
        s3_key = None

    if s3_key:
        try:
            return download_file_from_s3(s3_key, bucket_name=bucket_name, cache_dir=cache_dir)
        except Exception:
            return str(local_path)
    return str(local_path)


def upload_directory(local_dir: str, prefix: str, bucket_name: Optional[str] = None) -> List[str]:
    """로컬 디렉터리를 S3 prefix 아래에 업로드합니다."""
    bucket_name = bucket_name or os.getenv('S3_BUCKET_NAME')
    if not bucket_name:
        raise ValueError('S3_BUCKET_NAME이 .env에 설정되어 있지 않습니다.')

    source_dir = Path(local_dir)
    if not source_dir.exists():
        return []

    uploaded = []
    client = get_s3_client()
    for file_path in source_dir.rglob('*'):
        if not file_path.is_file():
            continue
        relative_key = file_path.relative_to(source_dir).as_posix()
        s3_key = f"{prefix.rstrip('/')}/{relative_key}".replace('//', '/')
        client.upload_file(str(file_path), bucket_name, s3_key)
        uploaded.append(f's3://{bucket_name}/{s3_key}')
    return uploaded
