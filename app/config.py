from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()  # 将操作系统中的环境变量读取一下

class Settings(BaseModel):  # BaseModel后续这个类会转换为JSON/字典方便使用

  # BaseModel后续这个类会转换为JSON/字典方便使用
        deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", 'https://api.deepseek.com/v1')
        deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "sk-a4cea0a8ffc14fd58f25b575cd2e573e")
        deepseek_model_name: str = os.getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat")
        qianwen_base_url: str = os.getenv("QIANWEN_BASE_URL", 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        qianwen_api_key: str = os.getenv("QIANWEN_API_KEY", "sk-d259b1addbe34a95910cfa1c46a9ec6b")
        qianwen_model_name: str = os.getenv("QIANWEN_MODEL_NAME", 'qwen-plus')
        qianwen_embedding_model_name: str = os.getenv("QIANWEN_EMBEDDING_MODEL_NAME", "text-embedding-v3")


        chroma_dir: str = os.getenv("CHROMA_DIR", "./data/chroma")
        chroma_host: str = os.getenv("CHROMA_HOST", "localhost")
        chroma_port: int = int(os.getenv("CHROMA_PORT", "8000"))
        collection_name: str = os.getenv("COLLECTION_NAME", "knowledge_base")
        chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
        chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
        audio_collection_name:str = os.getenv("AUDIO_COLLECTION_NAME", "audio_base")


        celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "amqp://peter:123456@127.0.0.1:5672/%2F")  # ⚠️改自己的用户名和密码
        celery_audio_queue: str = "audio"  # 消息队列的名字

        audio_dir: str = "data/audio"
        audio_wav_dir: str = "data/audio_wav"
        audio_clip_dir: str = "data/audio_clips"


        es_url: str = os.getenv("ES_URL", "http://127.0.0.1:9200")
        es_audio_index: str = os.getenv("ES_AUDIO_INDEX", "audio_segments_v1")

        audio_hybrid_top_v: int = int(os.getenv("AUDIO_HYBRID_TOP_V", "50"))
        audio_hybrid_top_b: int = int(os.getenv("AUDIO_HYBRID_TOP_B", "50"))
        audio_hybrid_top_n_rerank: int = int(os.getenv("AUDIO_HYBRID_TOP_N_RERANK", "30"))
        audio_rrf_k0: int = int(os.getenv("AUDIO_RRF_K0", "60"))

        audio_rerank_model: str = os.getenv("AUDIO_RERANK_MODEL", "BAAI/bge-reranker-base")
        audio_rerank_batch_size: int = int(os.getenv("AUDIO_RERANK_BATCH_SIZE", "16"))
        audio_rerank_max_len: int = int(os.getenv("AUDIO_RERANK_MAX_LEN", "512"))
        audio_rerank_min_score: float = float(os.getenv("AUDIO_RERANK_MIN_SCORE", "-1e9"))

settings = Settings()