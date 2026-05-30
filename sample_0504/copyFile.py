import os
import shutil

def copy_with_version(src_path):
    if not os.path.exists(src_path):
        print("❌ 파일이 존재하지 않습니다.")
        return None

    # 파일명 분리
    dir_name = os.path.dirname(src_path)
    base_name = os.path.basename(src_path)
    name, ext = os.path.splitext(base_name)

    version = 1
    new_name = f"{name}_v{version}{ext}"
    dst_path = os.path.join(dir_name, new_name)

    # 중복 체크하면서 버전 증가
    while os.path.exists(dst_path):
        version += 1
        new_name = f"{name}_v{version}{ext}"
        dst_path = os.path.join(dir_name, new_name)

    # 파일 복사
    shutil.copy(src_path, dst_path)

    return dst_path


# ✅ 사용자 입력 받기
src_file = input("복사할 파일명을 입력하세요: ").strip()

result = copy_with_version(src_file)

if result:
    print(f"✅ 파일 생성 완료: {result}")