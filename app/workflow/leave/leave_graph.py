from __future__ import annotations
import json
import re
import uuid
from typing import Dict,Any
from datetime import datetime,timedelta

from langgraph.graph import StateGraph,START,END
from langchain_core.messages import HumanMessage,SystemMessage
from app.prompts.prompt import *
from app.depts import get_llm
from app.workflow.leave.models import LeaveState
from app.workflow.leave.rules import validate_leave

from app.db.mysql import (
    get_leave_balance,
    insert_leave_request,
    get_leave_request,
    cancel_leave_request,
)

"------------helpers-----------------"
def _safe_json_load(s:str)->Dict[str,Any]:#这段代码需要根据具体的大模型输出做调整
    if not s:
        return {}
    s = s.strip()
    if s.startswith("'''"):
        s = s.strip("'")
        if s.lower().startswith("json"):
            s = s[4:].strip()
    try:
        return json.loads(s)#loads是将str的json变成字典
    except Exception:
        print("json解析错误")
        return {}

def _safe_iso(s:Any)-> str |None: #这个函数是为了验证s表示的时间是不是一个合法的日期时间
    if not s or not isinstance(s,str):
        return None
    s = s.strip()
    try:
        datetime.fromisoformat(s)
        return s
    except Exception:
        print("时间格式错误")
        return None

def _extract_leave_id(text:str)->str | None:#从大模型的结果中，将工单LV-这个内容抽出来
    if not text:
        return None
    m = re.search(r"\bLV-[0-9a-fA-F]{6,12}\b",text)
    #re.search用来查找text中有没有符合第一个包含查询结果的内容
    return m.group(0) if m else None #m.group(0)返回的是匹配到的内容

"------------------Intent Routing-----------------"

def decide_intent(state:LeaveState)->str:
    """ apply/query/cancel"""
    text = (state.get("text") or state.get("question") or "").lower()
    if any(k in text for k in ["取消","撤销","作废",]):
        return "cancel"
    if any(k in text for k  in ["查询","查","状态","进度","结果"]):
        if  any(k in text for k in ["请假","年假","病假","休假","调休","假期","事假"]):
            return "query"
    return "apply"

def intent_node(state:LeaveState)->dict:
    return {}

"-----------------Query/Cancel/Node----------------"

def query_leave_node(state:LeaveState)->dict:
    text = state.get("text") or state.get("question") or ""
    leave_id = state.get("leave_id") or _extract_leave_id(text)
    if not leave_id:
        return {"answer": "请输入工单编号(例如LV-XXXXXX)"}
    row = get_leave_id(text)
    if not row:
        return {"answer": "没有找到对应的工单"}
    return {
        "leave_id": leave_id,
        "answer": (
            f"请假单 {leave_id} 当前状态：{row['status']}\n"
            f"类型：{row['leave_type']}\n"
            f"开始：{row['start_time']}\n"
            f"结束：{row['end_time']}\n"
            f"时长：{row['duration_days']} 天\n"
            f"原因：{row.get('reason') or '无'}"
        ),
    }

def cancel_leave_node(state:LeaveState)->dict:
    text = state.get("text") or state.get("question") or ""
    leave_id = state.get("leave_id") or _extract_leave_id(text)
    if not leave_id:
        return {"answer": "请输入工单编号(例如LV-XXXXXX)"}
    ok = cancel_leave_request(leave_id)
    if not ok:
        return {"answer": "取消失败,未找到该单或单据不是待审批状态"}

    return {"answer": f"已取消请假单{leave_id}"}

"--------------Apply-flow Node---------------"

def parse_time_node(state:LeaveState)->dict:
    req = state.get("req") or {}
    if _safe_iso(req.get("start_time")) and _safe_iso(req.get("end_time")):
        return {}
    llm = get_llm()
    tetx = state.get("text","") or state.get("requester","") or  ""

    now = datatime.now().strftime("%Y-%m-%d %H:%M")

    messages = [
        SystemMessage(content=TIME_SYSTEM),
        HumanMessage(content=TIME_USER.format(now=now,text=text)),
    ]
    raw = llm.invoke(messages).content
    data = _safe_json_load(raw)

    start = _safe_iso(data.get("start_time"))
    end = _safe_iso(data.get("end_time"))

    if start or end:
        req.update({"start_time":start or req.get("start_time"),
                       "end_time":end or req.get("end_time")})
        return {"req": req}
    return {}


def extract_slots_node(state:LeaveState)->dict:
    llm =get_llm()
    tetx = state.get("text","") or state.get("requester","") or  ""
    message = [
        SystemMessage(content=SLOT_SYSTEM),
        HumanMessage(content=SLOT_USER.format(text=tetx))
    ]
    raw = llm.invoke(message).content
    data = _safe_json_load(raw)
    print("大模型的结果是-------------",data)

    req = state.get("req") or {}
    req.update({
        "leave_type":data.get("leave_type") or req.get("leave_type"),
        "start_time":_safe_iso(data.get("start_time")) or req.get("start_time"),
        "end_time":_safe_iso(data.get("end_time")) or req.get("end_time"),
        "reason":data.get("reason") or req.get("reason")
    })
    req["requester"] = state.get("requester","anonymous")
    return {"req": req}

def validate_node(state:LeaveState)->dict:
    req = state.get("req") or {}
    missing,violations = validate_leave(req,balances_days=5.0)
    return {"missing_fields":missing,"violations":violations,"req":req}

def decide_next(state:LeaveState)->str:
    if state.get("missing_fields") or state.get("violations"):
        return "need_info"
    return "confirm"

def need_info_node(state:LeaveState)->dict:
    missing = state.get("missing_fields") or []
    violations = state.get("violations") or []
    tips = []
    if missing:
        tips.append("缺少信息" + ", ".join(missing))
    if violations:
        tips.append("规则问题：" + "；".join(violations))
    return {"answer": ";".join(tips) + " 请补充信息。"}

def confirm_node(state:LeaveState)->dict:
    req = state.get("req") or {}
    ans = (
        "请确认你的请假信息: \n"
        f"- 类型：{req.get('leave_type')}\n"
        f"- 开始：{req.get('start_time')}\n"
        f"- 结束：{req.get('end_time')}\n"
        f"- 时长：{req.get('duration_days')} 天\n"
        f"- 原因：{req.get('reason') or '无'}\n"
        "回复“确认”提交，或直接回复修改后的信息。"
    )
    return {"answer": ans}

def decide_confirm(state:LeaveState)->str:
    text = (state.get("text") or "").strip().lower()
    if text in {"确认","yes","y","确定","ok"}:
        return "create"
    return "end"

def create_leave_node(state:LeaveState)->dict:
     leave_id = "LV-" + uuid.uuid4().hex[:8]
     return {"leave_id": leave_id,"answer":f"已为你提交申请，编号{leave_id},等待审批。"}

def build_leave_graph():
    g = StateGraph(LeaveState)
    #intent routing
    g.add_node("intent",intent_node)
    g.add_node("query",query_leave_node)
    g.add_node("cancel",cancel_leave_node)

    #apply flow
    g.add_node("parse_time",parse_time_node)
    g.add_node("extract",extract_slots_node)
    g.add_node("validate",validate_node)
    g.add_node("need_info",need_info_node)
    g.add_node("confirm",confirm_node)
    g.add_node("create",create_leave_node)

    g.add_edge(START,"intent")
    g.add_conditional_edges(
        "intent", decide_intent,
        {
            "query": "query",
            "cancel": "cancel",
            "apply": "parse_time"
        }
    )
    g.add_edge("parse_time","extract")
    g.add_edge("extract","validate")
    g.add_conditional_edges(
        "validate",decide_next,
        {
            "need_info": "need_info",
            "confirm": "confirm"},
    )

    g.add_conditional_edges("confirm",decide_confirm,
    {
                                "create": "create",
                                "end": END},
                            )

    g.add_edge("query",END)
    g.add_edge("cancel",END)
    g.add_edge("need_info",END)
    g.add_edge("create",END)
    return g.compile()



