# from langchain_core.prompts import ChatPromptTemplate
# from langchain_community.chat_models import ChatOllama

# prompt = ChatPromptTemplate.from_template(
#     "다음 질문에 답변해줘: {question}"
# )

# llm = ChatOllama(model="llama3")

# chain = prompt | llm

# result = chain.invoke({"question": "수박이란?"})
# print(result.content)
