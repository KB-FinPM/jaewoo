from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

prompt = ChatPromptTemplate.from_template(
    "다음 질문에 친절하게 답변해줘: {question}"
)

llm = ChatOpenAI(model="gpt-4o-mini")

chain = prompt | llm

result = chain.invoke({"question": "PM이 하는 일은?"})
print(result.content)
