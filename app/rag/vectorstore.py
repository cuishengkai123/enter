#这个文件的主要作用是对chromada进行配置
import chromadb
from langchain_chroma import Chroma
from app.config import settings

def get_vectorstore(embeddings):
    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port
    )
    return Chroma(  # 返回的就是一个指向chromadb的连接
        client=client,
        collection_name=settings.collection_name,  # 为我们这个项目建议一个专属的数据库
        embedding_function=embeddings,
    )
