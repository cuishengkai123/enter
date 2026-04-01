from langchain_core.messages import AIMessage, HumanMessage
from typing import TypedDict,List,Any
from langgraph.graph import StateGraph,START,END
from app.rag.prompts import QA_USER
from app.depts import get_vs
from app.depts import get_llm

class QAstate(TypedDict, total=False):
    question: str
    text:str
    user_role:str
    docs:List[Any]
    answer:str
    messages:List[Any]

def decide_retrieve(state:QAstate):
    """
    条件函数：决定走检索还是直答
    返回值必须对应 add_conditional_edges 的 key
    """
    return "retrieve" #返回"retrieve"，对应下面映射中的 key，跳到 retrieve_node 节点

def decide_retrieve_node(state:QAstate) ->dict:
    """
    节点runnable:必须返回dict
    这里只是一个no-op节点，真正路由在decide_retrieve（）里完成
    """
    return{} #返回一个空字典，表示什么也不做

def retrieve_node(state:QAstate)->dict:
    """
    从Chroma数据库里检索相关文档
    先按照visibility做过滤；如果元数据里没有该字段导致检索为空，
    则回退到无过滤检索。
    """
    vs = get_vs()
    role = state.get("user_role","public")
    query = state.get("question") or state.get("text") or ""
    retriever = vs.as_retriever(   #此处是在创建索引器
        search_kwargs={
            "k":8, #返回8条结果
            "filter":{"visibility":{"$in":["public",role]}} #只检索可见性为public的用户文档
        }
    )
    docs = retriever.invoke(query) #invoke就是真的去向量数据库里查询
    #docs表示从向量数据库里查出的文档
    if not docs: #如果上面查出东西，下面就不执行了
        retriever2 = vs.as_retriever(
            search_kwargs ={"k":8}
        )
        docs = retriever2.invoke(query)
        return {"docs":docs,"question":query,"debug":"filtered"}
    return {"docs": docs, "question": query, "debug": "filtered"}

def grade_evidence_node(state:QAstate)->str:
    """
    检索后判断是否有证据
    主要看有没有[1][3]
    """
    return "good" if state.get("docs") else "bad"

def generate_answer_node(state:QAstate)->dict:
    """带引用生成答案"""
    llm = get_llm()
    docs =state.get("docs",[])

    context = "\n\n".join(
        f"[{i+1}]{d.page_content}\n(source={d.metadata.get('source')},page = {d.metadata.get('page')})"
        for i ,d in enumerate(docs[:6])
    ) #将检索出来的内容拼接成一个大的字符串

    prompt = QA_USER.format(question = state["question"], context = context)
    messages = [
        AIMessage(content=QA_USER),
        HumanMessage(content=prompt)
    ]
    ans = llm.invoke(messages).content
    return {"answer":ans}

def refuse_or_clarify_node(state:QAstate)->dict:
    """
    无证据兜底
    """
    return {"answer":"我没有在当前文档中找到足够证据回答"}

def build_qa_graph():
    g = StateGraph(QAstate)

    g.add_node("decide_retrieve_node",decide_retrieve_node)#条件节点
    g.add_node("retrieve_node",retrieve_node)#检索
    g.add_node("generate_node",generate_answer_node)#带引用生成答案
    g.add_node("refuse_node",refuse_or_clarify_node)#无证据

    #State -> dicide_retrieve
    g.add_edge(START,"decide_retrieve_node")

    #decide_retrieve 的路由条件
    g.add_conditional_edges(
        "decide_retrieve_node", decide_retrieve, {
            "retrieve": "retrieve_node",  # ✅ 如果返回"retrieve"，就去 retrieve 节点
        },
    )
    #retrieve 后根据证据充分性路由
    g.add_conditional_edges("retrieve_node", grade_evidence_node, {
        "good": "generate_node",
        "bad": "refuse_node"
    })
    g.add_edge("generate_node", END)
    g.add_edge("refuse_node", END)

    return g.compile()



