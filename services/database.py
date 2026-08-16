import sqlite3
from datetime import datetime
import os



DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.db")


def init_db():
    """初始化数据库，创建对话历史表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content text NOT NULL,
        source TEXT DEFAULT '手动录入',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

    )
    cursor.execute(
        # 建 feedback 表：记录用户对回答的点赞/点踩（注释放 Python 层，不能进 SQL 字符串）
        """
        CREATE TABLE IF NOT EXISTS feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        # 建 session_meta 表：会话附加信息（自定义标题、置顶）
        """
        CREATE TABLE IF NOT EXISTS session_meta(
        session_id TEXT PRIMARY KEY,
        custom_title TEXT,
        is_pinned INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )



    conn.commit()
    conn.close()


def save_message(session_id: str, role: str, content: str):
    """保存一条消息到数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )

    conn.commit()
    conn.close()


def get_chat_history(session_id: str, limit: int = 10):
    """获取某个会话的最近 N 条消息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, content FROM chat_messages 
        WHERE session_id = ? 
        ORDER BY id DESC 
        LIMIT ?
        """,
        (session_id, limit)
    )

    messages = cursor.fetchall()
    conn.close()

    # 反转顺序，让最早的消息在前
    return [{"role": role, "content": content} for role, content in reversed(messages)]
def save_document(title,content,source = "手动录入"):
    """新增文档，返回doc_id"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (title,content,source) VALUES (?,?,?)",
        (title,content,source)
    )
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()
    return doc_id
def get_document(doc_id):
    """查询单篇文章"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, content, source, created_at, updated_at FROM documents WHERE id = ?",
        (doc_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id":row[0],
            "title":row[1],
            "content":row[2],
            "source":row[3],
            "created_at":row[4],
            "updated_at":row[5],
        }
    return None
def list_documents():
    """列出所有文档，只返回摘要"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, source, created_at, updated_at FROM documents ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "title": r[1], "source": r[2], "created_at": r[3], "updated_at": r[4]}

        for r in rows
        ]
def update_document(doc_id,title,content):
    """修改文档"""
    conn =sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE documents SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, content, doc_id)
    )
    conn.commit()
    conn.close()

def delete_document(doc_id):
    """删除文档"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM documents WHERE id = ?",(doc_id,)
    )
    conn.commit()
    conn.close()

def update_last_message(session_id,role,content):
    """更新某个会话里最后一条指定角色的消息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE chat_messages SET content = ? WHERE id = (SELECT id FROM chat_messages WHERE session_id = ? AND role = ? ORDER BY id DESC LIMIT 1)",
        (content, session_id, role)
    )
    conn.commit()
    conn.close()


def list_sessions():
    """列出所有会话：标题(优先自定义，否则第一条用户消息)、消息数、最后活动时间、是否置顶"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            cm.session_id,
            COALESCE(sm.custom_title, (
                SELECT content FROM chat_messages
                WHERE session_id = cm.session_id AND role = 'user'
                ORDER BY id ASC LIMIT 1
            )) AS title,
            COUNT(cm.id) AS message_count,
            (SELECT created_at FROM chat_messages
             WHERE session_id = cm.session_id
             ORDER BY id DESC LIMIT 1) AS updated_at,
            COALESCE(sm.is_pinned, 0) AS is_pinned
        FROM chat_messages cm
        LEFT JOIN session_meta sm ON sm.session_id = cm.session_id
        GROUP BY cm.session_id
        ORDER BY is_pinned DESC, updated_at DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "session_id": r[0],
            "title": (r[1] or "")[:30],
            "message_count": r[2],
            "updated_at": r[3],
            "is_pinned": bool(r[4]),
        }
        for r in rows
    ]


def delete_session(session_id: str):
    """删除某会话（全部消息 + 附加信息）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM session_meta WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def rename_session(session_id: str, title: str):
    """重命名会话：写入/更新自定义标题（UPSERT）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO session_meta (session_id, custom_title) VALUES (?, ?)
           ON CONFLICT(session_id) DO UPDATE SET custom_title = excluded.custom_title, updated_at = CURRENT_TIMESTAMP""",
        (session_id, title)
    )
    conn.commit()
    conn.close()


def set_session_pinned(session_id: str, pinned: bool):
    """置顶/取消置顶会话"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO session_meta (session_id, is_pinned) VALUES (?, ?)
           ON CONFLICT(session_id) DO UPDATE SET is_pinned = excluded.is_pinned, updated_at = CURRENT_TIMESTAMP""",
        (session_id, 1 if pinned else 0)
    )
    conn.commit()
    conn.close()
def get_session_messages(session_id: str):
    """获取某会话的全部消息（带 id，按时间正序）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, role, content, created_at FROM chat_messages
        WHERE session_id = ?
        ORDER BY id ASC
        """,
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "role": r[1], "content": r[2], "created_at": r[3]}
        for r in rows
    ]
def message_exists(message_id: int):
    # 定义函数：入参 message_id（整数）；返回 True/False 表示该消息是否存在
    conn = sqlite3.connect(DB_PATH)
    # 连接数据库
    cursor = conn.cursor()
    # 创建游标
    cursor.execute(
        "SELECT 1 FROM chat_messages WHERE id = ?",
        # 查消息表里有没有这条记录；SELECT 1 比 SELECT * 快，只关心"有没有"
        (message_id,)
        # 占位符实参
    )
    exists = cursor.fetchone() is not None
    # fetchone() 取一行：有记录返回元组，没有返回 None；is not None 转成布尔值
    conn.close()
    # 关闭连接
    return exists
    # 返回是否存在


def save_feedback(message_id: int, rating: int, comment: str = ""):
    # 定义函数：入参 message_id（消息ID）、rating（1或-1）、comment（可选，默认空串）；返回新反馈记录的ID
    conn = sqlite3.connect(DB_PATH)
    # 连接数据库
    cursor = conn.cursor()
    # 创建游标
    cursor.execute(
        "INSERT INTO feedback (message_id, rating, comment) VALUES (?, ?, ?)",
        # 插入一条反馈记录；? 占位符防注入
        (message_id, rating, comment)
        # 三个占位符的实参，顺序对应 SQL 里的三个字段
    )
    conn.commit()
    # 提交事务：INSERT 必须 commit 才真正写入磁盘
    feedback_id = cursor.lastrowid
    # lastrowid：刚插入这行的自增ID，作为返回值
    conn.close()
    # 关闭连接
    return feedback_id
    # 返回新记录ID（前端可用来定位这条反馈）

