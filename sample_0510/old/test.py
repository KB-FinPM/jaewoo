from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

response = llm.invoke("서울에서 가볼만한 곳 3곳 추천해줘")
print(response.content)
