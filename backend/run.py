# # 替换系统的 sqlite3 模块，用 pysqlite3 替代底层实现
# import pysqlite3
# import sys
# sys.modules['sqlite3'] = sys.modules['pysqlite3']

import uvicorn

if __name__ == "__main__":
    # uvicorn.run("app.main:app", host="0.0.0.0", port=8999, reload=True, reload_dirs=["app"])
    uvicorn.run("app.main:app", host="0.0.0.0", port=8999, reload=False)
