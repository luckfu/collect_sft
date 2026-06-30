from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import json
import logging
from aiohttp import web

class APIHandler(ABC):
    """API处理器基类，定义统一的接口"""
    
    def __init__(self, config: Dict[str, Any], async_logger: logging.Logger):
        self.config = config
        self.async_logger = async_logger
    
    @abstractmethod
    def get_endpoint_config(self, model: str) -> Optional[Dict[str, Any]]:
        """获取模型对应的端点配置"""
        pass
    
    @abstractmethod
    def prepare_headers(self, request_headers: Dict[str, str]) -> Dict[str, str]:
        """准备转发请求的头部"""
        pass
    
    @abstractmethod
    def get_target_url(self, endpoint_config: Dict[str, Any]) -> str:
        """获取目标URL"""
        pass
    
    @abstractmethod
    def parse_stream_chunk(self, line_str: str, complete_response: str, response_id: Optional[str]) -> Tuple[str, Optional[str], str]:
        """解析流式响应块，返回 (更新后的complete_response, response_id, 额外信息)"""
        pass
    
    @abstractmethod
    def parse_final_response(self, response_json: Dict[str, Any]) -> str:
        """解析最终响应内容"""
        pass
    
    @abstractmethod
    def get_api_name(self) -> str:
        """获取API名称，用于日志"""
        pass

class OpenAIHandler(APIHandler):
    """OpenAI API处理器"""
    
    def get_endpoint_config(self, model: str) -> Optional[Dict[str, Any]]:
        """获取OpenAI模型对应的端点配置"""
        if not self.config or "endpoints" not in self.config:
            return None
        
        for provider, config in self.config["endpoints"].items():
            if model in config.get("models", []):
                return {
                    "base_url": config["base_url"],
                    "path": config["chat_completion_path"]
                }
        return None
    
    def prepare_headers(self, request_headers: Dict[str, str]) -> Dict[str, str]:
        """准备OpenAI请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": request_headers.get("Authorization", "")
        }
    
    def get_target_url(self, endpoint_config: Dict[str, Any]) -> str:
        """获取OpenAI目标URL"""
        return f"{endpoint_config['base_url']}{endpoint_config['path']}"
    
    def parse_stream_chunk(self, line_str: str, complete_response: str, response_id: Optional[str]) -> Tuple[str, Optional[str], str]:
        """解析OpenAI流式响应块"""
        complete_reasoning = ""
        has_reasoning = False
        
        if line_str.startswith("data: "):
            if line_str.strip() == "data: [DONE]":
                return complete_response, response_id, complete_reasoning
            
            try:
                json_data = line_str[6:].strip()
                if json_data:
                    json_chunk = json.loads(json_data)
                    if "id" in json_chunk and not response_id:
                        response_id = json_chunk["id"]
                    if "choices" in json_chunk and json_chunk["choices"]:
                        delta = json_chunk["choices"][0].get("delta", {})
                        reasoning = delta.get("reasoning_content")
                        if reasoning is not None:
                            complete_reasoning += reasoning
                            has_reasoning = True
                        content = delta.get("content")
                        if content is not None:
                            complete_response += content
            except json.JSONDecodeError as json_err:
                # 日志记录在调用方处理
                pass
            except Exception:
                # 日志记录在调用方处理
                pass
        
        return complete_response, response_id, complete_reasoning
    
    def parse_final_response(self, response_json: Dict[str, Any]) -> str:
        """解析OpenAI最终响应内容"""
        if "choices" in response_json and response_json["choices"]:
            choice = response_json["choices"][0]
            if isinstance(choice, dict) and "message" in choice and isinstance(choice["message"], dict):
                reasoning_content = choice["message"].get("reasoning_content", "")
                response_content = choice["message"].get("content", "")
                return f"<think>\n{reasoning_content}\n</think>\n\n\n{response_content}" if reasoning_content else response_content
        return ""
    
    def get_api_name(self) -> str:
        return "OpenAI"

class AnthropicHandler(APIHandler):
    """Anthropic API处理器"""
    
    def get_endpoint_config(self, model: str) -> Optional[Dict[str, Any]]:
        """获取Anthropic模型对应的端点配置"""
        if not self.config or "endpoints" not in self.config:
            return None
        
        for provider, config in self.config["endpoints"].items():
            if model in config.get("models", []) and "anthropic_path" in config:
                return {
                    "base_url": config["base_url"],
                    "anthropic_path": config["anthropic_path"]
                }
        return None
    
    def prepare_headers(self, request_headers: Dict[str, str]) -> Dict[str, str]:
        """准备Anthropic请求头"""
        auth_header = request_headers.get("Authorization", "")
        api_key = ""
        if auth_header.startswith("Bearer "):
            api_key = auth_header.replace("Bearer ", "").strip()
        elif request_headers.get("x-api-key"):
            api_key = request_headers.get("x-api-key")
        
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    def get_target_url(self, endpoint_config: Dict[str, Any]) -> str:
        """获取Anthropic目标URL"""
        return f"{endpoint_config['base_url']}{endpoint_config['anthropic_path']}"
    
    def parse_stream_chunk(self, line_str: str, complete_response: str, response_id: Optional[str]) -> Tuple[str, Optional[str], str]:
        """解析Anthropic流式响应块"""
        if line_str.startswith("data: "):
            if line_str.strip() == "data: [DONE]":
                return complete_response, response_id, ""
            
            try:
                json_chunk = json.loads(line_str[6:])
                if "id" in json_chunk and not response_id:
                    response_id = json_chunk["id"]
                if "delta" in json_chunk:
                    content = json_chunk.get("delta", {}).get("text", "")
                    complete_response += content
            except json.JSONDecodeError:
                # 日志记录在调用方处理
                pass
        
        return complete_response, response_id, ""
    
    def parse_final_response(self, response_json: Dict[str, Any]) -> str:
        """解析Anthropic最终响应内容"""
        content_list = response_json.get("content", [])
        response_content = ""
        if isinstance(content_list, list) and content_list:
            for content_item in content_list:
                if isinstance(content_item, dict):
                    if content_item.get("type") == "text":
                        response_content += content_item.get("text", "")
                    elif content_item.get("type") == "tool_use":
                        tool_name = content_item.get("name", "")
                        tool_input = content_item.get("input", {})
                        response_content += f"\n[Tool: {tool_name}]\n{json.dumps(tool_input, ensure_ascii=False, indent=2)}\n"
        return response_content
    
    def get_api_name(self) -> str:
        return "Anthropic"

class APIHandlerFactory:
    """API处理器工厂类"""
    
    @staticmethod
    def create_handler(api_type: str, config: Dict[str, Any], async_logger: logging.Logger) -> APIHandler:
        """根据API类型创建对应的处理器"""
        if api_type == "openai":
            return OpenAIHandler(config, async_logger)
        elif api_type == "anthropic":
            return AnthropicHandler(config, async_logger)
        else:
            raise ValueError(f"不支持的API类型: {api_type}")