from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from config import settings


def is_enabled() -> bool:
    return bool(settings.dashscope_api_key_2 and settings.dashscope_base_url and settings.dashscope_chat_model)


def get_chat() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.dashscope_chat_model,
        base_url=settings.dashscope_base_url,
        api_key=settings.dashscope_api_key_2,
        temperature=0.2,
    )


def chat(system: str, user: str) -> str:
    client = get_chat()
    resp = client.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return resp.content
