import argparse

from modules.config import RECREATE_COLLECTION
from modules.pipeline import run_pipeline


def parse_args():
    parser = argparse.ArgumentParser(description='PM Agent document analyzer')
    parser.add_argument('--docx', default='구축요건정의서.v.1.docx', help='분석할 구축요건정의서 DOCX 파일 경로')
    parser.add_argument('--output-dir', default='output', help='산출물 출력 디렉토리')
    parser.add_argument('--recreate-collection', action='store_true', default=RECREATE_COLLECTION, help='Qdrant collection 재생성 여부')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    run_pipeline(docx_path=args.docx, output_dir=args.output_dir, recreate_collection=args.recreate_collection)
