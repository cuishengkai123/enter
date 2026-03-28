# app/deps.py

# --- 第一步：只导入第三方库 ---
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from app.rag.vectorstore import get_vectorstore

# --- 第二步：定义函数 (不要在这里使用 settings) ---
# 注意：此时不要调用 get_llm() 或 get_embeddings()，只定义函数

def get_llm():
    # 将 settings 的导入移到函数内部
    from app.config import settings
    return ChatOpenAI(
        base_url=settings.qianwen_base_url,
        api_key=settings.qianwen_api_key,
        model=settings.qianwen_model_name
    )

def get_embeddings():
    # 将 settings 的导入移到函数内部
    from app.config import settings
    return DashScopeEmbeddings(
        model=settings.qianwen_embedding_model_name,
        dashscope_api_key=settings.qianwen_api_key,
    )

def get_vs():
    # 确保 get_embeddings 已定义
    return get_vectorstore(get_embeddings())

def get_audio_vs():
    return get_audio_vectorstore(get_embeddings())


if __name__ == "__main__":
    resp = get_llm().invoke('你是谁？你的版本是什么？')
    print(resp.content)