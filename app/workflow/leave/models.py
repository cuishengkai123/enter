from enum import Enum
from typing import Optional,List,TypedDict,Any
from pydantic import BaseModel,Field

class LeaveType(str,Enum):
    annual = "annual" #年假
    sick = "sick" #病假
    personal = "personal" #事假
    other = "other" #其他假
    """
    这个类表示的是请假单，模型就是一组数据
    模型类对应关系数据库的表结构，一个对象对应表中的一行。这叫：“对象-关系映射ORM”
    """
class LeaveRequest(BaseModel):
    requester:str #请求者
    leave_type:LeaveType = LeaveType.annual #请假类型，默认是年假
    start_time:Optional[str] = None #Optional表示可选
    end_time:Optional[str] = None
    duration_days:Optional[float] = None # 请假天数
    reason:Optional[str] = None #请假原因

class LeaveState(TypedDict,total=False):
    text:str #原始文本
    requester:str #请求者
    user_role:str #角色

    req:dict #请求
    missing_fields:List[str] #缺失的字段
    violations:List[str] #违反的规则

    answer:str #回答
    confirmed:bool #是否符合规则
    leave_id:Optional[str] #请假编号

