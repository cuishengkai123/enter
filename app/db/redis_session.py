import json
import redis
from typing import Any

r = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=True,
)

TTL_SECONDS = 604800 #设置的过期时间

DROP_KEYS = {
    "docs","messages","chat_history","retrieved_docs"
}
#这是一个集合，集合存入的都是后面要存入redis的时候一些不要的键

def _safe_dumps(obj:Any)->str:
    return json.dumps(obj,ensure_ascii=False,default=str)

def load_session(session_id:str)->dict | None:
    s = r.get(session_id)
    return json.loads(s) if s else None

def save_session(session_id, state:dict)->None:
    safe_state ={k:v for k,v in state.items() if k not in DROP_KEYS}
    #这里是过滤，去掉不想要的键
    r.setex(session_id,TTL_SECONDS,_safe_dumps(safe_state))
    #setex(键，过期时间，值)
save_session('s1',{"a":1,"b":2})
print(load_session('s1'))