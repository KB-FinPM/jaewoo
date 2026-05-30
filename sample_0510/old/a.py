from langchain.prompts.prompt import PromptTemplate
from langchain_openai import ChatOpenAI

# @@@ 참고: OPENAI_API_KEY 환경 변수에 api key 선언 필요 @@@

# animal1, animal2를 input으로 받는 프롬프트 예시
my_prompt = """
두 가지 동물에 대한 비교를 3줄 요약으로 해주세요.
{animal1} vs {animal2}
"""

# 프롬프트 템플릿 선언
my_prompt_template = PromptTemplate(
    input_variables=["animal1", "animal2"], template=my_prompt
)

# OPENAI 모델 선언
llm = ChatOpenAI(temperature=0, model_name="gpt-4o-mini")

# 프롬프트 템플릿과 모델을 chain으로 연결
chain = my_prompt_template | llm

# chain 실행
res = chain.invoke(input={"animal1": "고양이", "animal2": "호랑이"})
print(res)
