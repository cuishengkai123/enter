from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from app.router_graph import router_graph
from app.depts import get_vs, get_embeddings
from app.ingestion.loader import load_single_file, split_with_visibility, load_docs, split_docs
from app.config import settings
import time
import uuid
from pathlib import Path
from typing import Optional
import chromadb


app = FastAPI(title = "Enterprise")
DATA_DOCS_DIR = Path("./data/docs")
DATA_DOCS_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS:dict[str,dict] = {}
class ChatRep(BaseModel):
    text:str
    user_role:str = "public"
    requests:str = "anonymous"
    mode:Optional[str] = None
    session_id:Optional[str] = None

class ChatResp(BaseModel):
    answer:str

@app.post("/chat",response_model=ChatResp)
def chat(req:ChatRep):
    payload = req.model_dump()
    sid = payload.get("session_id")
    if sid and sid in SESSIONS:#sid不空且在session这个变量里存在
        prev = SESSIONS[sid]
        merged = {**prev,**payload}
        merged["text"] = merged.get("text")
        payload = merged #这段是将旧的提问+回答和现在的提问合并然后准备重新送给大模型
    out = router_graph.invoke(payload)
    if sid:
        SESSIONS[sid] = {**payload,**out}
    return {"answer":out["answer"]}

@app.post("/ingest")
async def ingest(
        file:UploadFile = File(...),
        visibility: str = Form("public"),
        doc_id: Optional[str] = Form(None)):

    if not file.filename:
        raise HTTPException(status_code=400, detail="Empty filename")
    visibility = (visibility or "public").strip().lower()
    suffix = Path(file.filename).suffix
    safe_name = f"{int(time.time())}_{uuid.uuid4().hex}{suffix}"
    save_path = DATA_DOCS_DIR / safe_name

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400,detail="Empty file")
    save_path.write_bytes(content)

    docs = load_single_file(save_path)
    if not docs:
        raise HTTPException(status_code=400,detail=f"Unsupported or empty file type:{suffix}")
    chunks = split_with_visibility(docs,visibility=visibility,doc_id=doc_id)

    vs = get_vs()
    vs.add_documents(chunks)
    return {
        "save_as":str(save_path),
        "visibility":visibility,
        "doc_id":doc_id,
        "chunks":len(chunks)
    }

@app.post("/reindex")
def reindex(visibility_default:str = Form("public")):
    visibility_default = (visibility_default or "public").strip().lower()
    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port
    )
    client.get_or_create_collection(name=settings.collection_name)
    client.delete_collection(name=settings.collection_name)
    print("向量数据库已删除")

    vs = get_vs()
    raw_docs = load_docs(str(DATA_DOCS_DIR)) #我们存放文件的那个目录，云存储
    if not raw_docs:
        return {"chunks":0,"docs":0,"message":"no docs found in data"}
    chunks =split_docs(raw_docs)
    for c in chunks:
        c.metadata = dict(c.metadata or {})
        c.metadata.setdefault("visibility_default",visibility_default)
    vs.add_documents(chunks)
    print("向量数据库已重建")
    return {"docs":len(raw_docs),"chunks":len(chunks),"visibility_default":visibility_default}










