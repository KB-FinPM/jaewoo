# 1. https://ollama.com/ 설치 후 ollama pull llama3
# 2. pip install 목록들
# docx2txt langchain langchain-community langchain-ollama langchain-text-splitters ollama 
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaLLM

# 1. 문서 로드
loader = Docx2txtLoader ( "./files/sample1.docx" )

documents = loader.load ()

# 2. 텍스트 분할
splitter = RecursiveCharacterTextSplitter (
    chunk_size = 1000 ,
    chunk_overlap = 100
)
 
split_docs = splitter.split_documents ( documents )

print ( f"""분할된 문서 개수: { len ( split_docs ) }""" )
 
# 3. LLM 생성
# llm = ChatOllama ( model = "llama3" , temperature = 0 )
llm = OllamaLLM(model="llama3" , temperature = 0)

# 4. 분석 함수
def analyze_documents ( docs ):
    chunk_summaries = []
   
    # 각 chunk 분석
    for i , doc in enumerate ( docs ):
        prompt = f"""
        당신은 프로젝트 매니저(PM)입니다.
        아래 문서 내용을 간단히 요약하세요.
        **답변은 반드시 한글로 작성하세요.**
 
        문서:
        { doc.page_content }
        """ 
        response = llm.invoke ( prompt )
        chunk_summaries.append ( response )
        print ( f"[ { i + 1 } / { len ( docs ) } ] 분석 완료" )
 
    return chunk_summaries
 

# 5. 실행
chunk_results = analyze_documents ( split_docs )
 
# 6. 통합 분석
combined_summary = "\n".join( chunk_results )
final_prompt = f"""
당신은 프로젝트 매니저(PM)입니다.
아래는 문서의 여러 부분을 분석한 결과입니다.
이들을 종합하여 최종 정리하세요.
**답변은 반드시 한글로 작성하세요.**
 

분석 결과:
{ combined_summary }
 

최종 정리:
1. 주요 내용 요약
2. 일정 관련 내용
3. 리스크 요소
4. 실행해야 할 Action Item
"""

final_response = llm.invoke( final_prompt )

# 7. 최종 결과 출력
print ( "\n ===== 최종 분석 결과 =====" )
print ( final_response )