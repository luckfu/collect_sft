import json
import logging
import asyncio
import aiosqlite
import traceback
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Optional

# 配置日志
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.NullHandler())

# 异步日志类
class AsyncLogger:
    def __init__(self, name: str, log_file: str, level=logging.DEBUG):
        self.queue = Queue()
        self.logger = logging.getLogger(name)
        
        # 清除所有现有的处理器，防止重复日志
        if self.logger.handlers:
            for handler in self.logger.handlers[:]:  # 使用副本进行迭代
                self.logger.removeHandler(handler)
        
        self.logger.setLevel(level)
        self.logger.propagate = False  # 防止日志传播到根记录器
        
        # 创建文件处理器和控制台处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        console_handler = logging.StreamHandler()
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 设置队列处理器
        queue_handler = QueueHandler(self.queue)
        self.logger.addHandler(queue_handler)
        
        # 创建队列监听器
        self.listener = QueueListener(
            self.queue,
            file_handler,
            console_handler,
            respect_handler_level=True
        )
        self.listener.start()
    
    def __del__(self):
        self.listener.stop()
    
    async def debug(self, msg: str):
        self.logger.debug(msg)
    
    async def info(self, msg: str):
        self.logger.info(msg)
    
    async def warning(self, msg: str):
        self.logger.warning(msg)
    
    async def error(self, msg: str):
        self.logger.error(msg)

# 全局异步日志实例
_async_logger: Optional[AsyncLogger] = None

# 初始化异步日志
def init_async_logger(name: str, log_file: str, level=logging.DEBUG) -> AsyncLogger:
    """初始化并返回异步日志实例"""
    global _async_logger
    # 如果已存在实例，先尝试清理资源
    if _async_logger is not None:
        try:
            _async_logger.listener.stop()
        except Exception as e:
            logger.warning(f"停止现有日志监听器时出错: {e}")
    
    # 确保根日志配置不会干扰我们的日志器
    root_logger = logging.getLogger()
    root_level = root_logger.level
    
    # 创建新的实例
    _async_logger = AsyncLogger(name, log_file, level)
    
    # 恢复根日志器的级别
    root_logger.setLevel(root_level)
    
    return _async_logger

# 获取异步日志实例
def get_async_logger() -> Optional[AsyncLogger]:
    """获取全局异步日志实例"""
    return _async_logger

# 数据库路径全局变量
_db_path: str = "interactions.db"

# 初始化数据库路径
async def init_db_path(db_path: str = "interactions.db") -> str:
    """初始化数据库路径"""
    global _db_path
    _db_path = db_path
    # 测试连接并确保表存在
    conn = None
    try:
        conn = await aiosqlite.connect(db_path)
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                model TEXT,
                conversation TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        await conn.commit()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"初始化数据库时出错: {e}\n{traceback.format_exc()}")
        raise
    finally:
        if conn:
            await conn.close()
    return _db_path

# 简化版：直接创建数据库连接
async def get_db_connection() -> aiosqlite.Connection:
    """创建并返回一个新的数据库连接"""
    global _db_path
    try:
        conn = await aiosqlite.connect(_db_path)
        return conn
    except Exception as e:
        logger.error(f"创建数据库连接时出错: {e}\n{traceback.format_exc()}")
        raise

def format_to_sharegpt(model: str, messages: list, response: str) -> dict:
    """将对话格式化为目标格式"""
    system_message = ""
    conversations = []
    
    # 处理原始消息
    for msg in messages:
        if msg["role"] == "system":
            system_message = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
        else:
            # 将 user 转换为 human，assistant 转换为 gpt
            role = "human" if msg["role"] == "user" else "gpt"
            content = msg["content"]
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            elif not isinstance(content, str):
                content = str(content)
            conversations.append({
                "from": role,
                "value": content.strip()
            })
            
            # 如果消息中包含工具调用，添加相应的 function_call 和 observation
            if msg.get("tool_calls"):
                for tool_call in msg["tool_calls"]:
                    # 添加函数调用
                    conversations.append({
                        "from": "function_call",
                        "value": json.dumps(tool_call, ensure_ascii=False)
                    })
                    # 如果有工具调用结果，添加 observation
                    if "function" in tool_call and "output" in tool_call:
                        conversations.append({
                            "from": "observation",
                            "value": tool_call["output"]
                        })
    
    # 处理助手的回复
    conversations.append({
        "from": "gpt",
        "value": response.strip()
    })
    
    # 如果最后的响应包含工具调用，也需要添加
    try:
        response_data = json.loads(response)
        if isinstance(response_data, dict) and response_data.get("tool_calls"):
            for tool_call in response_data["tool_calls"]:
                conversations.append({
                    "from": "function_call",
                    "value": json.dumps(tool_call, ensure_ascii=False)
                })
    except json.JSONDecodeError:
        pass
    
    return {
        "conversations": conversations,
        "system": system_message,
        "tools": []  # 可以根据实际工具定义填充此字段
    }

def save_conversation(conn, response_id: str, model: str, conversation: dict):
    """保存对话数据到数据库（同步版本）"""
    try:
        with conn:
            c = conn.cursor()
            c.execute(
                """INSERT INTO interactions (id, model, conversation)
                VALUES (?, ?, ?)""",
                (response_id, model, json.dumps(conversation, ensure_ascii=False))
            )
    except Exception as e:
        logger.error(f"保存对话数据时发生错误: {e}")
        raise

async def save_conversation_async(conn, response_id: str, model: str, conversation: dict):
    """保存对话数据到数据库（异步版本）"""
    try:
        # 检查连接类型，确保使用正确的方法
        if isinstance(conn, aiosqlite.Connection):
            await conn.execute(
                """INSERT INTO interactions (id, model, conversation)
                VALUES (?, ?, ?)""",
                (response_id, model, json.dumps(conversation, ensure_ascii=False))
            )
            await conn.commit()
        else:
            # 如果不是异步连接，记录错误
            logger.error(f"错误的连接类型: {type(conn)}，需要aiosqlite.Connection")
            raise TypeError(f"需要aiosqlite.Connection类型，但收到了{type(conn)}")
    except Exception as e:
        logger.error(f"异步保存对话数据时发生错误: {e}")
        raise