import json
import time
import asyncio
from typing import Dict, Any, Optional
from aiohttp import web
import aiohttp
import traceback
from api_handlers import APIHandler, APIHandlerFactory
from utils import format_to_sharegpt

class UnifiedAPIProcessor:
    """统一的API请求处理器"""
    
    def __init__(self, config: Dict[str, Any], async_logger, http_session: aiohttp.ClientSession, queue_conversation_func):
        self.config = config
        self.async_logger = async_logger
        self.http_session = http_session
        self.queue_conversation_func = queue_conversation_func
    
    async def process_api_request(self, request: web.Request, api_type: str) -> web.StreamResponse:
        """统一处理API请求"""
        try:
            # 创建对应的API处理器
            handler = APIHandlerFactory.create_handler(api_type, self.config, self.async_logger)
            
            # 通用的请求预处理
            headers = dict(request.headers)
            request_data = await request.json()
            
            # 请求体大小检查
            if not await self._validate_request_size(request_data):
                return web.Response(
                    status=413, 
                    text=json.dumps({"error": "请求体过大，请减小输入数据大小或分批处理"})
                )
            
            # 日志记录
            await self._log_request_info(headers, request_data, handler.get_api_name())
            
            # 获取模型和端点配置
            model = request_data.get("model")
            endpoint_config = handler.get_endpoint_config(model)
            
            if not endpoint_config:
                await self.async_logger.warning(f"❌ 不支持的{handler.get_api_name()}模型: {model}")
                return web.Response(
                    status=400, 
                    text=json.dumps({"error": f"不支持的模型: {model}"})
                )
            
            # 准备请求头
            forward_headers = handler.prepare_headers(headers)
            
            # 获取目标URL
            target_url = handler.get_target_url(endpoint_config)
            
            # 判断是否为流式请求
            is_stream = request_data.get("stream", False)
            
            await self.async_logger.info(
                f"📡 转发{handler.get_api_name()}请求到: {endpoint_config['base_url']}, 流式: {is_stream}"
            )
            
            # 发送请求并处理响应
            return await self._handle_api_response(
                target_url, forward_headers, request_data, request, 
                handler, model, is_stream
            )
            
        except json.JSONDecodeError:
            await self.async_logger.error(f"❌ 无效的{api_type}请求数据格式")
            return web.Response(status=400, text=json.dumps({"error": "无效的请求数据格式"}))
        except Exception as e:
            await self.async_logger.error(f"处理{api_type}请求时发生错误: {e}\n{traceback.format_exc()}")
            return web.Response(status=500, text=json.dumps({"error": "服务器内部错误"}))
    
    async def _validate_request_size(self, request_data: Dict[str, Any]) -> bool:
        """验证请求体大小"""
        messages = request_data.get("messages", [])
        total_chars = sum(len(str(msg)) for msg in messages)
        max_chars = 8000000
        
        if total_chars > max_chars:
            await self.async_logger.warning(
                f"❌ 请求体过大: {total_chars} 字符，超过限制 {max_chars} 字符"
            )
            return False
        return True
    
    async def _log_request_info(self, headers: Dict[str, str], request_data: Dict[str, Any], api_name: str):
        """记录请求信息"""
        safe_headers = headers.copy()
        if "Authorization" in safe_headers:
            safe_headers["Authorization"] = "[REDACTED]"
        if "x-api-key" in safe_headers:
            safe_headers["x-api-key"] = "[REDACTED]"
        
        await self.async_logger.debug(f"📝 收到新的{api_name}请求")
        await self.async_logger.debug(f"请求头: {json.dumps(safe_headers, ensure_ascii=False, indent=2)}")
        await self.async_logger.debug(f"请求体: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
    
    async def _handle_api_response(self, target_url: str, forward_headers: Dict[str, str], 
                                 request_data: Dict[str, Any], request: web.Request,
                                 handler: APIHandler, model: str, is_stream: bool) -> web.StreamResponse:
        """处理API响应"""
        start_time = time.time()
        
        async with self.http_session.post(target_url, headers=forward_headers, json=request_data) as resp:
            elapsed_time = time.time() - start_time
            await self.async_logger.info(f"{handler.get_api_name()}请求耗时: {elapsed_time:.2f}秒")
            
            if resp.status != 200:
                response_text = await resp.text()
                await self.async_logger.error(f"❌ {handler.get_api_name()}目标服务器错误: {response_text}")
                return web.Response(
                    status=resp.status, 
                    text=json.dumps({"error": f"目标服务器错误: {response_text}"})
                )
            
            await self.async_logger.info(f"✅ 成功接收到{handler.get_api_name()}服务器响应")
            
            if is_stream:
                return await self._handle_stream_response(resp, request, handler, model, request_data)
            else:
                return await self._handle_non_stream_response(resp, handler, model, request_data)
    
    async def _handle_stream_response(self, resp: aiohttp.ClientResponse, request: web.Request,
                                    handler: APIHandler, model: str, request_data: Dict[str, Any]) -> web.StreamResponse:
        """处理流式响应"""
        response = web.StreamResponse(
            status=200, 
            headers={
                "Content-Type": "text/event-stream", 
                "Cache-Control": "no-cache", 
                "Connection": "keep-alive"
            }
        )
        await response.prepare(request)
        await self.async_logger.info(f"🌊 开始处理{handler.get_api_name()}流式响应")
        
        complete_response = ""
        complete_reasoning = ""
        response_id = None
        saved_to_db = False
        
        try:
            async for line in resp.content:
                line_str = line.decode("utf-8")
                
                # 写入响应到客户端
                try:
                    await response.write(line)
                except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as conn_err:
                    await self.async_logger.info(f"🔌 客户端连接已断开: {conn_err}")
                    break
                except Exception as write_err:
                    if "Cannot write to closing transport" in str(write_err) or "SSL" in str(write_err):
                        await self.async_logger.info(f"🔌 客户端连接已关闭: {write_err}")
                        break
                    else:
                        await self.async_logger.warning(f"⚠️ 写入响应时发生错误: {write_err}")
                        break
                
                # 解析响应内容
                if line_str.startswith("data: "):
                    if line_str.strip() == "data: [DONE]":
                        if response_id and not saved_to_db:
                            await self._save_conversation(
                                response_id, model, request_data, complete_response, complete_reasoning
                            )
                            saved_to_db = True
                        break
                    
                    # 使用处理器解析流式响应块
                    try:
                        complete_response, response_id, reasoning = handler.parse_stream_chunk(
                            line_str, complete_response, response_id
                        )
                        if reasoning:  # 只有OpenAI会返回reasoning
                            complete_reasoning += reasoning
                    except Exception as parse_err:
                        await self.async_logger.warning(
                            f"⚠️ {handler.get_api_name()}流式响应解析错误: {parse_err}"
                        )
                        continue
        
        except (aiohttp.ClientConnectionError, aiohttp.ClientPayloadError) as client_err:
            if "SSL" in str(client_err) or "APPLICATION_DATA_AFTER_CLOSE_NOTIFY" in str(client_err):
                await self.async_logger.info(f"🔌 上游服务器连接正常关闭: {client_err}")
            else:
                await self.async_logger.warning(f"⚠️ 上游连接异常: {client_err}")
        except Exception as e:
            await self.async_logger.error(f"{handler.get_api_name()}流式响应处理错误: {e}")
        finally:
            # 确保保存对话
            if response_id and not saved_to_db and complete_response:
                await self._save_conversation(
                    response_id, model, request_data, complete_response, complete_reasoning
                )
        
        return response
    
    async def _handle_non_stream_response(self, resp: aiohttp.ClientResponse, 
                                        handler: APIHandler, model: str, 
                                        request_data: Dict[str, Any]) -> web.Response:
        """处理非流式响应"""
        response_json = await resp.json()
        await self.async_logger.info(f"✅ {handler.get_api_name()}非流式响应处理完成")
        
        response_id = response_json.get("id")
        if response_id:
            # 使用处理器解析最终响应
            response_content = handler.parse_final_response(response_json)
            if response_content:
                formatted_conversation = format_to_sharegpt(
                    model, request_data.get('messages', []), response_content
                )
                await self.queue_conversation_func(
                    id=response_id,
                    model=model,
                    conversation=formatted_conversation
                )
        
        return web.Response(
            status=200, 
            body=json.dumps(response_json, ensure_ascii=False).encode('utf-8'), 
            content_type="application/json"
        )
    
    async def _save_conversation(self, response_id: str, model: str, request_data: Dict[str, Any],
                               complete_response: str, complete_reasoning: str = ""):
        """保存对话到数据库"""
        final_response = complete_response
        if complete_reasoning:  # 只有OpenAI有reasoning
            final_response = f"<think>\n{complete_reasoning}\n</think>\n\n\n{complete_response}"
        
        formatted_conversation = format_to_sharegpt(
            model, request_data.get('messages', []), final_response
        )
        await self.queue_conversation_func(
            id=response_id,
            model=model,
            conversation=formatted_conversation
        )