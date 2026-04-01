
import pymysql

# 数据库配置
conn = pymysql.connect(
    host="127.0.0.1",
    port=3306,
    user="tom",
    password="123456",
    database="enterprise_kb",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

try:
    with conn.cursor() as cur:
        # 检查表是否存在
        print("=" * 60)
        print("检查 leave_requests 表")
        print("=" * 60)

        cur.execute("SHOW TABLES LIKE 'leave_requests'")
        table_exists = cur.fetchone()

        if table_exists:
            print("✅ leave_requests 表存在\n")

            # 查看表结构
            print("表结构:")
            cur.execute("DESCRIBE leave_requests")
            columns = cur.fetchall()
            for col in columns:
                print(f"  - {col['Field']}: {col['Type']} {col['Null']} {col['Key']}")

            print("\n" + "=" * 60)
            print("所有请假记录:")
            print("=" * 60)

            # 查询所有记录
            cur.execute("SELECT * FROM leave_requests ORDER BY created_at DESC")
            rows = cur.fetchall()

            if rows:
                print(f"共找到 {len(rows)} 条记录:\n")
                for row in rows:
                    print("-" * 60)
                    for key, value in row.items():
                        print(f"{key}: {value}")
                    print()
            else:
                print("❌ 表中没有任何记录")
        else:
            print("❌ leave_requests 表不存在！")
            print("\n可能需要先创建表结构。")

finally:
    conn.close()
