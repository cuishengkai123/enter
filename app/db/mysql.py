
import os
import pymysql
from contextlib import contextmanager

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "tom")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123456")
MYSQL_DB = os.getenv("MYSQL_DB", "enterprise_kb")

@contextmanager
def get_conn():  # 获取数据库连接
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT,
        user=MYSQL_USER, password=MYSQL_PASSWORD,
        database=MYSQL_DB, charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        yield conn
    finally:
        conn.close()


def get_leave_balance(requester: str) -> dict | None:
    """根据用户名 requester 查询这个用户还有几天年假，病假。。。可以请"""
    print(f"\n🔍 [DEBUG] 查询余额 - requester={requester}")
    print(f"[DEBUG] 数据库配置：{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}, 用户：{MYSQL_USER}")

    with get_conn() as conn:
        with conn.cursor() as cur:
            # 检查表是否存在
            cur.execute("SHOW TABLES LIKE 'leave_balances'")
            table_exists = cur.fetchone()
            print(f"[DEBUG] 表 leave_balances 存在：{'✅' if table_exists else '❌'}")

            if table_exists:
                # 查看所有记录
                cur.execute("SELECT requester, annual_days, sick_days, personal_days FROM leave_balances")
                all_records = cur.fetchall()
                print(f"[DEBUG] 表中所有记录:")
                for rec in all_records:
                    print(f"  - {rec}")

                # 查询特定用户
                cur.execute(
                    "SELECT annual_days, sick_days, personal_days FROM leave_balances WHERE requester=%s",
                    (requester,)
                )
                result = cur.fetchone()
                print(f"[DEBUG] 查询结果：{result}")

                if result:
                    print(f"✅ 用户 {requester} 的年假余额：{result.get('annual_days')} 天")
                else:
                    print(f"❌ 未找到用户 {requester} 的记录")

                return result
            else:
                print("❌ 表不存在！")
                return None


def insert_leave_request(req: dict) -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO leave_requests
                (leave_id, requester, leave_type, start_time, end_time, duration_days, reason, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'PENDING')
                """,
                (
                    req["leave_id"], req["requester"], req["leave_type"],
                    req["start_time"], req["end_time"], req["duration_days"],
                    req.get("reason")
                )
            )
    return req["leave_id"]


def get_leave_request(leave_id: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM leave_requests WHERE leave_id=%s", (leave_id,))
            return cur.fetchone()


def cancel_leave_request(leave_id: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE leave_requests SET status='CANCELLED' WHERE leave_id=%s AND status='PENDING'",
                (leave_id,)
            )
            return cur.rowcount > 0


def approve_leave_request(leave_id: str, approver: str = "admin") -> bool:
    """审批通过请假单"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE leave_requests SET status='APPROVED', approver=%s WHERE leave_id=%s AND status='PENDING'",
                (approver, leave_id)
            )
            return cur.rowcount > 0


def reject_leave_request(leave_id: str, approver: str = "admin", reason: str = None) -> bool:
    """驳回请假单"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE leave_requests SET status='REJECTED', approver=%s, reject_reason=%s WHERE leave_id=%s AND status='PENDING'",
                (approver, reason, leave_id)
            )
            return cur.rowcount > 0


def get_recent_leave_requests(requester: str, limit: int = 5) -> list:
    """获取最近的请假申请记录"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT leave_id, requester, leave_type, start_time, end_time, duration_days, status, created_at
                FROM leave_requests
                WHERE requester=%s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (requester, limit)
            )
            return cur.fetchall()


def update_leave_request(leave_id: str, data: dict) -> bool:
    """更新请假单信息"""
    with get_conn() as conn:
        with conn.cursor() as cur:
            fields = []
            values = []
            for k, v in data.items():
                fields.append(f"{k}=%s")
                values.append(v)
            
            sql = f"UPDATE leave_requests SET {','.join(fields)} WHERE leave_id=%s AND status='PENDING'"
            values.append(leave_id)
            
            cur.execute(sql, tuple(values))
            return cur.rowcount > 0


if __name__ == "__main__":
    print("=" * 50)
    print("测试数据库查询")
    print("=" * 50)
    result = get_leave_balance('peter')
    print(f"\n最终返回：{result}")

