
import json
import logging
import time
import asyncio
import uuid
from aiohttp import web
import aiohttp
import argparse
from typing import Dict, Any, Optional, Set
import traceback
import sqlite3
import aiosqlite
from utils import format_to_sharegpt, init_async_logger, get_async_logger, init_db_path, get_db_connection, save_conversation_async
import re
from aiohttp.web_middlewares import middleware
from collections import defaultdict, deque
import hashlib
from unified_api_processor import UnifiedAPIProcessor

# 自定义日志过滤器，屏蔽探针请求的日志
class ProbeRequestFilter(logging.Filter):
    """过滤探针请求的日志记录"""
    
    def __init__(self):
        super().__init__()
        # 定义探针请求的特征模式
        self.probe_patterns = [
            r'GET / HTTP',  # 根路径探测
            r'GET /favicon.ico',  # 图标请求
            r'GET /\.well-known/',  # 安全文件探测
            r'GET /locales/',  # 本地化文件探测
            r'UNKNOWN / HTTP',  # 未知协议请求
            r'CensysInspect',  # Censys扫描器
            r'Mozilla/5\.0.*Chrome/90\.0\.4430\.85',  # 特定的探针User-Agent
            r'Go-http-client',  # Go客户端探测
            r'BadHttpMessage',  # HTTP协议错误
            r'BadStatusLine',  # HTTP状态行错误
            r'Invalid method encountered',  # 无效HTTP方法
            r'Pause on PRI/Upgrade',  # HTTP/2升级错误
            r"'NoneType' object is not callable",  # 空对象调用错误
            r'Task exception was never retrieved',  # 异步任务异常
            r'Error handling request',  # 请求处理错误
            r'193\.34\.212\.110',  # 特定的探针IP
            r'185\.191\.127\.222',  # 特定的探针IP
            r'162\.142\.125\.124',  # 特定的探针IP
            r'194\.62\.248\.69',  # 特定的探针IP
            r'209\.38\.219\.203',  # 特定的探针IP
            r'\\x16\\x03\\x01',  # SSL/TLS握手数据
            r'bytearray\(b\'\\x16\\x03\\x01',  # SSL握手字节数组
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.probe_patterns]
    
    def filter(self, record):
        """过滤日志记录，如果是探针请求则不记录"""
        message = record.getMessage()
        
        # 检查是否匹配探针请求模式
        for pattern in self.compiled_patterns:
            if pattern.search(message):
                return False  # 不记录此日志
        
        return True  # 记录此日志

# 配置日志
def parse_args():
    parser = argparse.ArgumentParser(description='Proxy Endpoint Server')
    parser.add_argument('--config', type=str, default='endpoint_config.json', help='配置文件路径')
    parser.add_argument('--port', type=int, default=8080, help='服务器端口')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='日志级别')
    return parser.parse_args()

args = parse_args()

# 只设置基本日志级别，不添加处理器，避免重复日志
logging.basicConfig(level=getattr(logging, args.log_level.upper()))
logger = logging.getLogger(__name__)
# 移除所有处理器，防止重复日志
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# 创建探针请求过滤器实例
probe_filter = ProbeRequestFilter()

# 为aiohttp的访问日志和服务器错误日志添加过滤器
aiohttp_access_logger = logging.getLogger('aiohttp.access')
aiohttp_server_logger = logging.getLogger('aiohttp.server')
asyncio_logger = logging.getLogger('asyncio')

# 添加过滤器到所有相关的日志记录器
for log in [aiohttp_access_logger, aiohttp_server_logger, asyncio_logger]:
    log.addFilter(probe_filter)
    # 为每个处理器也添加过滤器
    for handler in log.handlers:
        handler.addFilter(probe_filter)

# 全局异步异常处理器
def handle_asyncio_exception(loop, context):
    """处理asyncio中未捕获的异常"""
    exception = context.get('exception')
    if exception:
        # 检查是否为SSL连接关闭相关的异常
        if ('SSL' in str(exception) and 
            ('APPLICATION_DATA_AFTER_CLOSE_NOTIFY' in str(exception) or 
             'Connection lost' in str(exception))):
            # 这是正常的SSL连接关闭，不记录错误日志
            return
        
        # 检查是否为其他常见的连接断开异常
        if any(error_type in str(exception) for error_type in [
            'Cannot write to closing transport',
            'Connection reset by peer',
            'Connection aborted',
            'Broken pipe'
        ]):
            # 这些都是正常的连接断开，不记录错误日志
            return
    
    # 对于其他异常，使用默认处理
    message = context.get('message', 'Unhandled exception in async task')
    logger.warning(f"Asyncio异常: {message}, 异常: {exception}")

# 探针请求拦截中间件
@middleware
async def probe_request_middleware(request, handler):
    """拦截探针请求的中间件"""
    
    # 定义合法的API路径
    valid_paths = [
        '/v1/chat/completions',
        '/chat/completions', 
        '/v1/embeddings',
        '/v1/rerank',
        '/health',
        '/anthropic/v1/messages'
    ]
    
    # 检查请求路径是否合法
    path = request.path.lower()
    is_valid_path = any(path == valid_path or path.endswith(valid_path) for valid_path in valid_paths)
    
    # 检查User-Agent是否为已知的探针
    user_agent = request.headers.get('User-Agent', '').lower()
    probe_user_agents = [
        'censysinspect',
        'go-http-client',
        'chrome/90.0.4430.85',  # 常见的探针UA
        'mozilla/5.0 (windows nt 10.0; win64; x64) applewebkit/537.36 (khtml, like gecko) chrome/90.0.4430.85 safari/537.36 edg/90.0.818.46'
    ]
    
    is_probe_ua = any(probe_ua in user_agent for probe_ua in probe_user_agents)
    
    # 检查客户端IP是否为已知的探针IP
    client_ip = request.remote
    probe_ips = [
        '193.34.212.110',
        '185.191.127.222', 
        '162.142.125.124',
        '194.62.248.69',
        '209.38.219.203'
    ]
    
    is_probe_ip = client_ip in probe_ips
    
    # 检查是否为常见的探针路径
    probe_paths = [
        '/',
        '/favicon.ico',
        '/.well-known/security.txt',
        '/locales/locale.json'
    ]
    
    is_probe_path = path in probe_paths
    
    # 如果是无效路径、探针请求、探针IP或探针路径，直接返回404，不记录日志
    if not is_valid_path or is_probe_ua or is_probe_ip or is_probe_path:
        # 静默返回404，不产生任何日志
        return web.Response(status=404, text='Not Found')
    
    # 对于合法请求，继续处理
    return await handler(request)

class ProxyEndpoint:
    def __init__(self, config_path: str = "endpoint_config.json", port: int = 8080):
        # 创建应用时添加中间件
        self.app = web.Application(middlewares=[probe_request_middleware])
        self.config_path = config_path
        self.port = port
        
        # 缓存配置 - 必须在load_config()之前初始化
        self.model_endpoint_cache: Dict[str, Dict[str, Any]] = {}
        self.config_cache_time: float = 0
        self.config_cache_ttl: float = 300  # 5分钟缓存
        
        self.setup_routes()
        self.load_config()
        self.async_logger: Optional[logging.Logger] = None  # 添加类型提示，确保不为 None
        
        # 性能优化：创建全局HTTP客户端会话和连接池
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.db_pool: Optional[aiosqlite.Connection] = None
        
        # 统一API处理器
        self.api_processor: Optional[UnifiedAPIProcessor] = None
        
        self.app.on_startup.append(self.init_async_resources)
        self.app.on_cleanup.append(self.cleanup_resources)
    
    def setup_routes(self):
        self.app.router.add_post("/v1/chat/completions", self.handle_chat_completions)
        self.app.router.add_post("/chat/completions", self.handle_chat_completions)
        self.app.router.add_post("/v1/embeddings", self.handle_embeddings)
        self.app.router.add_post("/v1/rerank", self.handle_rerank)
        self.app.router.add_get("/health", self.handle_health_check)
        self.app.router.add_post("/anthropic/v1/messages", self.handle_anthropic_messages)
        
    async def init_async_resources(self, app):
        """初始化异步资源（日志、数据库和连接池）"""
        # 设置全局异步异常处理器
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(handle_asyncio_exception)
        
        # 初始化异步日志
        await asyncio.to_thread(init_async_logger, "proxy_endpoint", "proxy_endpoint.log", getattr(logging, args.log_level.upper()))
        self.async_logger = get_async_logger()
        if self.async_logger is None:
            raise ValueError("Failed to initialize async_logger")
        await self.async_logger.info("✅ 异步日志初始化完成")
        await self.async_logger.info("✅ 全局异步异常处理器已设置")
        
        # 初始化数据库
        await init_db_path("interactions.db")
        await self.async_logger.info("✅ 数据库初始化完成")
        
        # 性能优化：初始化HTTP连接池
        connector = aiohttp.TCPConnector(
            limit=100,  # 总连接池大小
            limit_per_host=30,  # 每个主机的连接数限制
            ttl_dns_cache=300,  # DNS缓存时间
            use_dns_cache=True,
            keepalive_timeout=30,  # 保持连接时间
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=600,  # 总超时时间
            connect=30,  # 连接超时
            sock_connect=30,  # Socket连接超时
            sock_read=600  # Socket读取超时
        )
        
        self.http_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'ProxyEndpoint/1.0'}
        )
        
        await self.async_logger.info("✅ HTTP连接池初始化完成")
        
        # 预热模型端点缓存
        self._refresh_model_cache()
        await self.async_logger.info("✅ 模型端点缓存初始化完成")
        
        # 性能优化：初始化批量处理队列
        self.conversation_queue = asyncio.Queue(maxsize=1000)
        self.batch_size = 10
        self.batch_timeout = 5.0  # 5秒超时
        
        # 启动批量处理任务
        asyncio.create_task(self._batch_save_conversations())
        await self.async_logger.info("✅ 批量处理队列初始化完成")
        
        # 初始化统一API处理器
        self.api_processor = UnifiedAPIProcessor(
            config=self.config,
            async_logger=self.async_logger,
            http_session=self.http_session,
            queue_conversation_func=self._queue_conversation
        )
        await self.async_logger.info("✅ 统一API处理器初始化完成")
    
    async def cleanup_resources(self, app):
        """清理资源"""
        if self.http_session:
            await self.http_session.close()
            await self.async_logger.info("✅ HTTP连接池已关闭")
        
        if self.db_pool:
            await self.db_pool.close()
            await self.async_logger.info("✅ 数据库连接池已关闭")
    
    async def _batch_save_conversations(self):
        """批量保存对话到数据库"""
        batch = []
        last_save_time = time.time()
        
        while True:
            try:
                # 等待新的对话数据或超时
                try:
                    conversation_data = await asyncio.wait_for(
                        self.conversation_queue.get(), 
                        timeout=self.batch_timeout
                    )
                    batch.append(conversation_data)
                except asyncio.TimeoutError:
                    # 超时，如果有数据就保存
                    if batch:
                        await self._save_batch(batch)
                        batch.clear()
                        last_save_time = time.time()
                    continue
                
                # 检查是否达到批量大小或超时
                current_time = time.time()
                if (len(batch) >= self.batch_size or 
                    current_time - last_save_time >= self.batch_timeout):
                    await self._save_batch(batch)
                    batch.clear()
                    last_save_time = current_time
                    
            except Exception as e:
                if self.async_logger:
                    await self.async_logger.error(f"批量保存对话时出错: {e}")
                # 清空批次，避免重复错误
                batch.clear()
                await asyncio.sleep(1)
    
    async def _save_batch(self, batch):
        """保存一批对话数据"""
        if not batch:
            return
            
        try:
            # 批量保存到数据库
            async with aiosqlite.connect("interactions.db") as conn:
                for conversation_data in batch:
                    await conn.execute(
                        "INSERT INTO interactions (id, model, conversation) VALUES (?, ?, ?)",
                        (
                            conversation_data['id'],
                            conversation_data['model'],
                            json.dumps(conversation_data['conversation'], ensure_ascii=False)
                        )
                    )
                await conn.commit()
            
            if self.async_logger:
                await self.async_logger.debug(f"✅ 批量保存 {len(batch)} 条对话记录")
                
        except Exception as e:
            if self.async_logger:
                await self.async_logger.error(f"批量保存失败: {e}")
    
    async def _queue_conversation(self, id: str, model: str, conversation: dict):
        """将对话数据添加到队列中"""
        try:
            conversation_data = {
                'id': id,
                'model': model,
                'conversation': conversation
            }
            await self.conversation_queue.put(conversation_data)
        except asyncio.QueueFull:
            if self.async_logger:
                await self.async_logger.warning("对话队列已满，丢弃数据")
        except Exception as e:
            if self.async_logger:
                await self.async_logger.error(f"添加对话到队列失败: {e}")
        
    async def handle_embeddings(self, request: web.Request) -> web.Response:
        # 获取原始请求的headers和body
        headers = dict(request.headers)
        request_data = await request.json()
        
        # 检查请求体大小
        input_text = request_data.get("input", "")
        if isinstance(input_text, list):
            total_chars = sum(len(str(text)) for text in input_text)
        else:
            total_chars = len(str(input_text))
            
        # 设置最大请求大小限制（约8MB）
        max_chars = 8000000
        if total_chars > max_chars:
            await self.async_logger.warning(f"❌ 请求体过大: {total_chars} 字符，超过限制 {max_chars} 字符")
            return web.Response(
                status=413,
                text=json.dumps({"error": "请求体过大，请减小输入数据大小或分批处理"})
            )
            
        # 记录原始请求信息
        await self.async_logger.debug("📝 收到新的embeddings请求")
        # 创建请求头的副本并移除敏感信息
        safe_headers = headers.copy()
        if "Authorization" in safe_headers:
            safe_headers["Authorization"] = "[REDACTED]"
        #await self.async_logger.debug(f"请求头: {json.dumps(safe_headers, ensure_ascii=False, indent=2)}")
        #await self.async_logger.debug(f"请求体: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
        
        # 检查并移除dimensions字段
        ##if "dimensions" in request_data:
        ##    dimensions_value = request_data["dimensions"]
        ##    await self.async_logger.info(f"🔄 移除请求中的dimensions字段，原始值: {dimensions_value}")
        ##    del request_data["dimensions"]
        
        # 获取模型对应的端点配置
        model = request_data.get("model")
        await self.async_logger.info(f"📝 处理embeddings模型请求: {model}")
        
        # 查找支持embeddings的端点
        endpoint_config = None
        for provider, config in self.config.get("endpoints", {}).items():
            if "embeddings_models" in config and model in config.get("embeddings_models", []):
                endpoint_config = {
                    "base_url": config["base_url"],
                    "path": config["embeddings_path"]
                }
                break
        
        if not endpoint_config:
            await self.async_logger.warning(f"❌ 不支持的embeddings模型: {model}")
            return web.Response(
                status=400,
                text=json.dumps({"error": f"不支持的embeddings模型: {model}"})
            )
        
        # 创建新的headers，保持原始认证信息和Content-Length
        forward_headers = {
            "Content-Type": "application/json",
            "Authorization": headers.get("Authorization", ""),
            "x-api-key": headers.get("x-api-key", "")
        }
        
        # 记录请求开始时间
        start_time = time.time()
        
        try:
            target_url = f"{endpoint_config['base_url']}{endpoint_config['path']}"
            async with self.http_session.post(
                target_url,
                headers=forward_headers,
                data=await request.read()  # 使用原始请求体数据
            ) as resp:
                    # 记录请求耗时
                    elapsed_time = time.time() - start_time
                    await self.async_logger.info(f"embeddings请求耗时: {elapsed_time:.2f}秒")
                    
                    if resp.status != 200:
                        error_text = await resp.text()
                        await self.async_logger.error(f"❌ embeddings目标服务器错误: {error_text}")
                        return web.Response(
                            status=resp.status,
                            text=json.dumps({"error": f"embeddings目标服务器错误: {error_text}"})
                        )
                    
                    # 处理响应
                    try:
                        response_text = await resp.text()
                        response_json = json.loads(response_text)
                        await self.async_logger.info("✅ embeddings响应处理完成")
                        #await self.async_logger.debug(f"响应内容: {json.dumps(response_json, ensure_ascii=False, indent=2)}")
                        
                        return web.Response(
                            status=200,
                            body=json.dumps(response_json, ensure_ascii=False).encode('utf-8'),
                            content_type="application/json"
                        )
                    except aiohttp.ClientPayloadError as e:
                        await self.async_logger.error(f"❌ 响应数据传输错误: {e}")
                        return web.Response(status=500, text=json.dumps({"error": "响应数据传输错误，请重试"}))
        except json.JSONDecodeError:
            await self.async_logger.error("❌ 无效的embeddings请求数据格式")
            return web.Response(status=400, text=json.dumps({"error": "无效的请求数据格式"}))
        except Exception as e:
            await self.async_logger.error(f"处理embeddings请求时发生错误: {e}\n{traceback.format_exc()}")
            return web.Response(status=500, text=json.dumps({"error": "服务器内部错误"}))

    def load_config(self):
        """从配置文件加载端点配置（带缓存）"""
        current_time = time.time()
        
        # 检查缓存是否有效
        if (hasattr(self, 'config') and self.config and 
            current_time - self.config_cache_time < self.config_cache_ttl):
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
                self.config_cache_time = current_time
                logger.info(f"✅ 成功加载配置文件: {self.config_path}")
                # 刷新模型端点缓存
                self._refresh_model_cache()
        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            self.config = {}
    
    def _refresh_model_cache(self):
        """刷新模型端点缓存"""
        self.model_endpoint_cache.clear()
        
        if not self.config or "endpoints" not in self.config:
            return
        
        for provider, config in self.config["endpoints"].items():
            # 缓存聊天模型
            for model in config.get("models", []):
                if "chat_completion_path" in config:
                    self.model_endpoint_cache[model] = {
                        "type": "chat",
                        "base_url": config["base_url"],
                        "path": config["chat_completion_path"]
                    }
            
            # 缓存embedding模型
            for model in config.get("embeddings_models", []):
                self.model_endpoint_cache[model] = {
                    "type": "embeddings",
                    "base_url": config["base_url"],
                    "path": config["embeddings_path"]
                }
            
            # 缓存rerank模型
            for model in config.get("rerank_models", []):
                self.model_endpoint_cache[model] = {
                    "type": "rerank",
                    "base_url": config["base_url"],
                    "path": "/v1/rerank"
                }
            
            # 缓存Anthropic模型
            for model in config.get("models", []):
                if "anthropic_path" in config:
                    self.model_endpoint_cache[f"{model}_anthropic"] = {
                        "type": "anthropic",
                        "base_url": config["base_url"],
                        "anthropic_path": config["anthropic_path"]
                    }
    
    def get_endpoint_for_model(self, model: str) -> Optional[Dict[str, Any]]:
        """根据模型名称获取对应的端点配置（使用缓存）"""
        # 首先检查缓存
        if model in self.model_endpoint_cache:
            cache_entry = self.model_endpoint_cache[model]
            # 根据缓存信息找到完整配置
            for provider, config in self.config.get("endpoints", {}).items():
                if config["base_url"] == cache_entry["base_url"]:
                    return {
                        "base_url": config["base_url"],
                        "path": config.get("chat_completion_path", "/v1/chat/completions")
                    }
        
        # 缓存未命中，回退到原始逻辑
        if not self.config or "endpoints" not in self.config:
            return None
        
        for provider, config in self.config["endpoints"].items():
            if model in config.get("models", []):
                return {
                    "base_url": config["base_url"],
                    "path": config["chat_completion_path"]
                }
            elif model in config.get("rerank_models", []):
                return {
                    "base_url": config["base_url"],
                    "path": config.get("rerank_path", "/v1/rerank")
                }
        
        logger.warning(f"⚠️ 未找到模型 {model} 的端点配置")
        return None

    def get_endpoint_for_anthropic_model(self, model: str) -> Optional[Dict[str, Any]]:
        """根据模型名称获取对应的 Anthropic 端点配置"""
        if not self.config or "endpoints" not in self.config:
            logger.error("❌ 配置文件中缺少endpoints配置")
            return None
        
        for provider, config in self.config["endpoints"].items():
            if model in config.get("models", []) and "anthropic_path" in config:
                return {
                    "base_url": config["base_url"],
                    "anthropic_path": config["anthropic_path"]
                }
        
        logger.warning(f"⚠️ 未找到 Anthropic 模型 {model} 的端点配置")
        return None



    async def handle_rerank(self, request: web.Request) -> web.Response:
        # 获取原始请求的headers和body
        headers = dict(request.headers)
        request_data = await request.json()
        
        # 获取模型对应的端点配置
        model = request_data.get("model")
        await self.async_logger.info(f"📝 处理rerank模型请求: {model}")
        
        # 查找支持rerank的端点
        endpoint_config = self.get_endpoint_for_model(model)
        
        if not endpoint_config:
            await self.async_logger.warning(f"❌ 不支持的rerank模型: {model}")
            return web.Response(
                status=400,
                text=json.dumps({"error": f"不支持的rerank模型: {model}"})
            )
        
        # 创建新的headers，保持原始认证信息
        forward_headers = {
            "Content-Type": "application/json",
            "Authorization": headers.get("Authorization", "")
        }
        
        # 记录请求开始时间
        start_time = time.time()
        
        try:
            target_url = f"{endpoint_config['base_url']}{endpoint_config['path']}"
            async with self.http_session.post(
                target_url,
                headers=forward_headers,
                json=request_data
            ) as resp:
                    # 记录请求耗时
                    elapsed_time = time.time() - start_time
                    await self.async_logger.info(f"rerank请求耗时: {elapsed_time:.2f}秒")
                    
                    if resp.status != 200:
                        error_text = await resp.text()
                        await self.async_logger.error(f"❌ rerank目标服务器错误: {error_text}")
                        return web.Response(
                            status=resp.status,
                            text=json.dumps({"error": f"rerank目标服务器错误: {error_text}"})
                        )
                    
                    # 处理响应
                    try:
                        response_text = await resp.text()
                        response_json = json.loads(response_text)
                        await self.async_logger.info("✅ rerank响应处理完成")
                        
                        return web.Response(
                            status=200,
                            body=json.dumps(response_json, ensure_ascii=False).encode('utf-8'),
                            content_type="application/json"
                        )
                    except aiohttp.ClientPayloadError as e:
                        await self.async_logger.error(f"❌ 响应数据传输错误: {e}")
                        return web.Response(status=500, text=json.dumps({"error": "响应数据传输错误，请重试"}))
        except json.JSONDecodeError:
            await self.async_logger.error("❌ 无效的rerank请求数据格式")
            return web.Response(status=400, text=json.dumps({"error": "无效的请求数据格式"}))
        except Exception as e:
            await self.async_logger.error(f"处理rerank请求时发生错误: {e}\n{traceback.format_exc()}")
            return web.Response(status=500, text=json.dumps({"error": "服务器内部错误"}))

    async def handle_health_check(self, request: web.Request) -> web.Response:
        """健康检查端点"""
        health_data = {
            "status": "ok",
            "timestamp": time.time(),
            "service": "proxy_endpoint",
            "version": "1.0.0"
        }
        return web.Response(
            status=200, 
            text=json.dumps(health_data, ensure_ascii=False),
            content_type="application/json"
        )

    async def handle_chat_completions(self, request: web.Request) -> web.StreamResponse:
        """处理OpenAI聊天补全请求"""
        return await self.api_processor.process_api_request(request, "openai")
    async def handle_anthropic_messages(self, request: web.Request) -> web.StreamResponse:
        """处理Anthropic消息请求"""
        return await self.api_processor.process_api_request(request, "anthropic")


if __name__ == "__main__":
    args = parse_args()
    proxy = ProxyEndpoint(config_path=args.config, port=args.port)
    try:
        web.run_app(proxy.app, host="0.0.0.0", port=args.port)
    except Exception as e:
        logger.error(f"启动服务器时发生致命错误: {e}", exc_info=True)
    finally:
        logger.info("服务器已关闭")
