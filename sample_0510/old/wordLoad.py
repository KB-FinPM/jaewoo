from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaLLM
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings

loader = UnstructuredWordDocumentLoader("sample-10pages.docx")
documents = loader.load()

# 결과 확인
# for doc in documents:
#     print(doc.page_content)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100
)

split_docs = text_splitter.split_documents(documents)

llm = OllamaLLM(model="llama3")

for doc in split_docs:
    response = llm.invoke(doc.page_content)
    # print(response.content)

vectorstore = FAISS.from_documents(
    split_docs,
    OpenAIEmbeddings()
)

retriever = vectorstore.as_retriever()

query = "이 문서의 주요 내용은?"
docs = retriever.get_relevant_documents(query)

for d in docs:
    print(d.page_content)