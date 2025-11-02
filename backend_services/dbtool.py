import pymysql
host = '---'
port = '---'
db = '---'
user = '---'
password = '---'


# ---- 用pymysql 操作数据库
def get_connection():
    conn = pymysql.connect(host=host, port=port, db=db, user=user, password=password)
    return conn


# ---- 使用 with 的方式来优化代码
class UsingMysql(object):

    def __init__(self, commit=True):
        self._commit = commit

    def __enter__(self):
        # 在进入的时候自动获取连接和cursor
        conn = get_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        conn.autocommit = False

        self._conn = conn
        self._cursor = cursor
        return self

    def __exit__(self, *exc_info):
        # 提交事务
        if self._commit:
            self._conn.commit()
        # 在退出的时候自动关闭连接和cursor
        self._cursor.close()
        self._conn.close()
    
     # ---- 查询方法 ----
    
    def fetch_one(self, sql, params=None):
        """查询单条记录"""
        self.cursor.execute(sql, params or ())
        return self.cursor.fetchone()
    
    def fetch_all(self, sql, params=None):
        """查询所有记录"""
        self.cursor.execute(sql, params or ())
        return self.cursor.fetchall()
    
    def fetch_many(self, sql, size=None, params=None):
        """查询指定数量的记录"""
        self.cursor.execute(sql, params or ())
        return self.cursor.fetchmany(size)

    @property
    def cursor(self):
        return self._cursor
