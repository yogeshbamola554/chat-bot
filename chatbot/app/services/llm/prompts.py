from langchain.prompts import ChatPromptTemplate

structured_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI that understands user input. 
    Always reply in JSON with:
    - intent
    - code
    - explanation"""),
    ("human", "{user_input}")
])
