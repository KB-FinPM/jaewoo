import os
from pathlib import Path
from PIL import Image
import pytesseract
from datetime import datetime


def get_image_files(folders):
    """지정된 폴더에서 모든 이미지 파일 수집"""
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.JPG', '.JPEG', '.PNG')
    image_files = []
    
    for folder in folders:
        folder_path = Path(folder)
        # print(f"📁 확인 중: {folder_path}")
        # print(f"   절대 경로: {folder_path.absolute()}")
        # print(f"   존재 여부: {folder_path.exists()}")
        
        if folder_path.exists() and folder_path.is_dir():
            print(f"   ✓ 폴더 발견!")
            files_in_folder = list(folder_path.rglob('*'))
            print(f"   폴더 내 전체 파일: {len(files_in_folder)}개")
            
            for file in sorted(folder_path.rglob('*')):
                if file.is_file() and file.suffix.lower() in image_extensions:
                    print(f"   - {file.name} 추가됨")
                    image_files.append(file)
        else:
            print(f"   ✗ 폴더 없음")
    
    return image_files


def extract_ocr_text(image_path):
    """이미지에서 OCR 텍스트 추출"""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang="kor+eng")
        return text.strip()
    except Exception as e:
        return f"[OCR 오류] {str(e)}"


def process_images_ocr():
    """AI1, AI2 폴더의 모든 이미지를 읽어서 result.txt로 생성"""
    # OCR 폴더 기준으로 files 경로 설정
    base_path = Path(__file__).parent.parent / "OCR/files"
    folders = [
        base_path / "AI1",
        base_path / "AI2",
    ]
    
    image_files = get_image_files(folders)
    
    if not image_files:
        print("❌ 이미지 파일을 찾을 수 없습니다.")
        return
    
    output_file = Path(__file__).parent.parent / "OCR/result.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # f.write("=" * 80 + "\n")
        # f.write("OCR 처리 결과\n")
        # f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        # f.write("=" * 80 + "\n\n")
        
        # f.write(f"총 이미지 파일 수: {len(image_files)}\n\n")
        
        for idx, image_path in enumerate(image_files, 1):
            # f.write(f"[{idx}] {image_path.name}\n")
            # f.write(f"    경로: {image_path}\n")
            
            ocr_text = extract_ocr_text(image_path)
            # f.write(f"    OCR 결과:\n")
            
            # 텍스트를 들여쓰기와 함께 작성
            for line in ocr_text.split('\n'):
                f.write(f"    {line}\n")
            
            # f.write("\n" + "-" * 80 + "\n\n")
        
        # f.write("=" * 80 + "\n")
        # f.write("처리 완료\n")
        # f.write("=" * 80 + "\n")
    
    print(f"✅ result.txt가 생성되었습니다.")
    print(f"   처리된 이미지 파일 수: {len(image_files)}")
    print(f"   저장 위치: {output_file}")


if __name__ == "__main__":
    process_images_ocr()