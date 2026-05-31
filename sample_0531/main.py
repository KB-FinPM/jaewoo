import argparse

from modules.config import AUTHOR_NAME, OUTPUT_MAPPER_PATH, PROJECT_NAME, RECREATE_COLLECTION
from modules.pipeline import run_pipeline


def parse_args():
    parser = argparse.ArgumentParser(description='PM Agent document analyzer')
    parser.add_argument('--docx', default=None, help='분석할 DOCX 파일 경로. 미입력 시 input/구축요건정의서.v.#.docx 중 가장 높은 버전을 자동 선택')
    parser.add_argument('--output-dir', default='output', help='산출물 출력 디렉토리')
    parser.add_argument('--recreate-collection', action='store_true', default=RECREATE_COLLECTION, help='Qdrant collection 재생성 여부')
    parser.add_argument('--project-name', default=PROJECT_NAME, help='산출물 표지에 입력할 프로젝트명')
    parser.add_argument('--author', default=AUTHOR_NAME, help='산출물 개정이력에 입력할 작성자명')
    parser.add_argument('--mapper', default=OUTPUT_MAPPER_PATH, help='산출물 템플릿/시트/컬럼/PPT 매핑 JSON 경로')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    run_pipeline(
        docx_path=args.docx,
        output_dir=args.output_dir,
        recreate_collection=args.recreate_collection,
        project_name=args.project_name,
        author=args.author,
        mapper_path=args.mapper,
    )
