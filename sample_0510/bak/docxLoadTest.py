import json

from modules.docx_loader import extract_docx_section
from modules.input_default import input_with_default
from modules.text_analyzer import analyze_text_chunks
from modules.request_document_analyzer import request_document_analyzer


# =========================
# 사용자 입력
# =========================

# 입력예시
print("입력예시(그냥 엔터시 자동입력됨)\n- 파일명 : ./탬플릿/01.구축요건정의서/KB스타뱅킹전용플레임워크구축.docx")
print("- 시작제목 : 1. 프로젝트 구축 내용")
print("- 종료제목 : 2. 시스템 구성 내역\n")

file_path = input_with_default(
    "DOCX 파일명 입력",
    "./탬플릿/01.구축요건정의서/KB스타뱅킹전용플레임워크구축.docx"
)

start_title = input_with_default(
    "시작 제목 입력",
    "1. 프로젝트 구축 내용"
)

end_title = input_with_default(
    "종료 제목 입력",
    "2. 시스템 구성 내역"
)

# =========================
# 함수 호출
# =========================

results = extract_docx_section(
    file_path=file_path,
    start_title=start_title,
    end_title=end_title
)

# =====================================
# Chunk 분석
# =====================================

chunk_summaries = analyze_text_chunks(results)

results = request_document_analyzer(chunk_summaries)

print(" \n\n\n ===== 최종 분석 결과 =====")
print(results)


print("\n✅ 완료")