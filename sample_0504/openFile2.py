from docx import Document

doc = Document("./탬플릿/01.구축요건정의서/KB스타뱅킹전용플레임워크구축.docx")

for para in doc.paragraphs:

    style = para.style.name
    text = para.text.strip()

    if not text or style.startswith("Normal"):
        continue

    print(f"[{style}] {text}")
    


