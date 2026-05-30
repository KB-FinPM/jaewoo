from urllib import response
 

from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama.chat_models import ChatOllama
from datetime import datetime
 

# 1. 문서 로드
# loader = UnstructuredWordDocumentLoader("./files/file-sample_100kB.docx")
# loader = Docx2txtLoader("./files/sample1.docx")#22개
loader = Docx2txtLoader("./files/sample2.docx") #3개
# loader = Docx2txtLoader("./files/sample3.docx") #1개
 

documents = loader.load ()
 

# 2. 텍스트 분할
splitter = RecursiveCharacterTextSplitter (
    chunk_size = 1000 ,
    chunk_overlap = 100
)
 

split_docs = splitter.split_documents(documents)
 

now = datetime.now(). strftime("%Y-%m-%d %H:%M:%S")
print(f"[{now}] 분할된 문서 개수: {len(split_docs)} ")
 

# 3. LLM 생성(qwen:0.5b, mistral, llama3)
llm = ChatOllama(model = "llama3" , temperature = 0.2 , system = "모든 답변은 반드시 자연스러운 한국어로 작성하세요.")
token_summaries = [ 0 , 0 ]   # [입력 토큰 총합, 출력 토큰 총합]
 

# 4. 분석 함수
def analyze_documents(docs):
    chunk_summaries = []
   
    # 각 chunk 분석
    for i , doc in enumerate(docs):
        prompt = f"""
        당신은 프로젝트 매니저(PM)입니다.
        아래 문서 내용을 간단히 요약하세요.
 

        문서:
        {doc .page_content}
        """
 

        response = llm.invoke(prompt)
        chunk_summaries.append(response.content)
        meta = response.response_metadata
 

        now = datetime.now(). strftime("%Y-%m-%d %H:%M:%S")       
        print(f"[{now}] [ {i + 1} / {len(docs)} ] 분석 완료")
 

        token_summaries [ 0 ] += meta.get('prompt_eval_count' , 0)  # 입력 토큰 합산
        token_summaries [ 1 ] += meta.get('eval_count' , 0)# 출력 토큰 합산
 

    return chunk_summaries
 

# 5. 실행
chunk_results = analyze_documents(split_docs)
 

# 6. 통합 분석
combined_summary = "\n".join(chunk_results)
final_prompt = f"""
당신은 프로젝트 매니저(PM)입니다.
아래는 문서의 여러 부분을 분석한 결과입니다.
이들을 종합하여 최종 정리하세요.
 

분석 결과:
{combined_summary}
 

최종 정리:
1. 주요 내용 요약
2. 일정 관련 내용
3. 리스크 요소
4. 실행해야 할 Action Item
"""
 

final_response = llm.invoke(final_prompt)
 

meta = final_response.response_metadata
token_summaries [ 0 ] += meta.get('prompt_eval_count' , 0)  # 입력 토큰 합산
token_summaries [ 1 ] += meta.get('eval_count' , 0)# 출력 토큰 합산
 

# 7. 최종 결과 출력
print(" \n ===== 최종 분석 결과 =====")
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"[{now}] {final_response.content} ")
print(f" \n 입력 토큰, 출력 토큰, 토큰 합계 : {token_summaries [ 0 ]} / {token_summaries [ 1 ]} / {token_summaries [ 0 ] + token_summaries [ 1 ]} ")