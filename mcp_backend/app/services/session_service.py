import os
import json
import time
import uuid
import logging
import asyncio
from typing import Dict, List, Any, Optional
from loguru import logger

# 会话数据保存目录
SESSION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'sessions')
# 会话超时时间(秒)
SESSION_TIMEOUT = 3600  # 默认1小时

class Message:
    """消息类，表示会话中的一条消息"""
    
    def __init__(self, role: str, content: Any, timestamp: Optional[float] = None):
        self.id = str(uuid.uuid4())
        self.role = role  # 'user', 'assistant', 'system', 'tool'
        self.content = content
        self.timestamp = timestamp or time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }
    
    def to_llm_message(self) -> Dict[str, Any]:
        """转换为LLM API格式的消息"""
        if self.role == "tool":
            # 根据MCP Python SDK规范，tool消息必须包含tool_call_id
            tool_call_id = self.content.get("tool_call_id", "unknown_call")
            content_text = self.content.get("text", "")
            
            # 标准工具响应消息格式
            return {
                "role": self.role,
                "tool_call_id": tool_call_id,
                "content": content_text
            }
        elif self.role == "assistant" and isinstance(self.content, dict) and "tool_calls" in self.content:
            # 助手消息包含工具调用
            result = {
                "role": self.role,
                "content": self.content.get("text", ""),
            }
            
            # 如果content为空，设置为null（某些API要求）
            if not result["content"]:
                result["content"] = None
            
            # 添加工具调用
            if self.content["tool_calls"]:
                result["tool_calls"] = self.content["tool_calls"]
                
            return result
        else:
            # 普通消息
            content = self.content
            if isinstance(content, dict) and "text" in content:
                content = content["text"]
                
            return {
                "role": self.role,
                "content": content
            }

class Session:
    """会话类，表示一个用户与系统的会话"""
    
    def __init__(self, session_id: Optional[str] = None, title: str = "新会话"):
        self.id = session_id or str(uuid.uuid4())
        self.title = title
        self.messages: List[Message] = []
        self.created_at = time.time()
        self.updated_at = time.time()
        self.metadata: Dict[str, Any] = {}
        self.llm_provider: Optional[str] = None
        self.llm_model: Optional[str] = None
        self.mcp_server_id: Optional[str] = None
    
    def add_message(self, role: str, content: Any) -> Message:
        """添加新消息到会话"""
        message = Message(role, content)
        self.messages.append(message)
        self.updated_at = time.time()
        return message
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """获取所有消息"""
        return [msg.to_dict() for msg in self.messages]
    
    def get_llm_messages(self) -> List[Dict[str, Any]]:
        """获取适用于LLM API的消息格式"""
        messages = []
        
        for msg in self.messages:
            try:
                llm_msg = msg.to_llm_message()
                messages.append(llm_msg)
            except Exception as e:
                logger.error(f"转换消息格式失败: {e}, 消息: {msg.to_dict()}")
        
        logger.debug(f"转换后的LLM消息格式: {messages}")
        return messages
    
    def clear_messages(self) -> None:
        """清空所有消息"""
        self.messages = []
        self.updated_at = time.time()
    
    def set_llm_info(self, provider: str, model: str) -> None:
        """设置LLM提供者和模型信息"""
        self.llm_provider = provider
        self.llm_model = model
        self.updated_at = time.time()
    
    def set_mcp_server(self, server_id: str) -> None:
        """设置MCP服务器ID"""
        self.mcp_server_id = server_id
        self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "mcp_server_id": self.mcp_server_id
        }

# 创建会话服务类，使用异步方法
class SessionService:
    """会话服务类，提供异步会话管理功能"""
    
    def __init__(self, timeout_seconds: int = SESSION_TIMEOUT):
        self.timeout_seconds = timeout_seconds
        
        # 确保会话目录存在
        try:
            os.makedirs(SESSION_DIR, exist_ok=True)
            logger.info(f"会话数据目录: {SESSION_DIR}")
            
            # 检查是否能读写会话目录
            test_file = os.path.join(SESSION_DIR, "test_session_dir.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            logger.info("会话目录读写权限检查通过")
            
            # 加载现有会话数量
            session_files = [f for f in os.listdir(SESSION_DIR) if f.endswith('.json')]
            logger.info(f"发现 {len(session_files)} 个现有会话")
            
        except Exception as e:
            logger.error(f"初始化会话目录失败: {e}")
            # 仍然创建目录，但记录错误
            os.makedirs(SESSION_DIR, exist_ok=True)
    
    async def get_sessions(self) -> List[Dict[str, Any]]:
        """获取所有会话，并检查超时状态"""
        sessions = []
        
        try:
            session_files = os.listdir(SESSION_DIR)
            for filename in session_files:
                if filename.endswith('.json'):
                    session_id = filename[:-5]  # 去掉.json后缀
                    try:
                        session = await self.get_session(session_id)
                        if session:
                            # 添加到列表前检查会话是否超时
                            await self._check_session_timeout(session)
                            sessions.append(session)
                    except Exception as e:
                        logger.error(f"加载会话 {session_id} 失败: {str(e)}")
        except Exception as e:
            logger.error(f"读取会话目录失败: {str(e)}")
        
        return sessions
    
    async def create_session(self, title: str, llm_provider: Optional[str] = None, 
                            llm_model: Optional[str] = None, mcp_server_id: Optional[str] = None) -> Dict[str, Any]:
        """创建新会话"""
        # 确保会话目录存在
        os.makedirs(SESSION_DIR, exist_ok=True)
        
        session_id = str(uuid.uuid4())
        created_at = int(time.time())
        
        session_data = {
            "id": session_id,
            "title": title,
            "name": title,  # 同时设置name字段，确保前后端一致
            "created_at": created_at,
            "updated_at": created_at,
            "last_activity": created_at,  # 最后活动时间
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "mcp_server_id": mcp_server_id,
            "messages": []
        }
        
        # 保存会话
        await self._save_session(session_id, session_data)
        
        return session_data
    
    async def get_session(self, id: str) -> Dict[str, Any]:
        """获取会话详情，并检查超时状态"""
        session_path = os.path.join(SESSION_DIR, f"{id}.json")
        
        if not os.path.exists(session_path):
            logger.warning(f"会话文件不存在: {session_path}")
            return {}
        
        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
                
                # 确保基本字段存在
                if "id" not in session:
                    session["id"] = id
                if "created_at" not in session:
                    session["created_at"] = int(time.time())
                if "updated_at" not in session:
                    session["updated_at"] = int(time.time())
                if "last_activity" not in session:
                    session["last_activity"] = int(time.time())
                if "messages" not in session:
                    session["messages"] = []
                
                # 检查会话是否超时
                await self._check_session_timeout(session)
                return session
        except json.JSONDecodeError:
            logger.error(f"会话文件 {id} 包含无效的JSON数据")
            return {"id": id, "title": "无效会话", "created_at": int(time.time()), "updated_at": int(time.time()), "last_activity": int(time.time()), "messages": []}
        except Exception as e:
            logger.error(f"读取会话 {id} 失败: {str(e)}")
            return {}
    
    async def update_session(self, id: str, **update_data) -> Dict[str, Any]:
        """更新会话信息
        
        Args:
            id: 会话ID
            **update_data: 更新数据，可以包含title, llm_provider, llm_model, mcp_server_id
            
        Returns:
            Dict[str, Any]: 更新后的会话数据
        """
        session = await self.get_session(id)
        
        if not session:
            raise ValueError(f"会话 {id} 不存在")
        
        # 检查会话是否超时
        if session.get('timed_out'):
            raise ValueError(f"会话 {id} 已超时，无法更新")
        
        # 处理字段名称映射 (前端可能使用name，而不是title)
        if "name" in update_data and update_data["name"] is not None:
            update_data["title"] = update_data.pop("name")
        
        # 更新会话属性
        if "title" in update_data and update_data["title"] is not None:
            session["title"] = update_data["title"]
            # 同时设置name字段，确保两者保持一致
            session["name"] = update_data["title"]
        
        if "llm_provider" in update_data and update_data["llm_provider"] is not None:
            session["llm_provider"] = update_data["llm_provider"]
        
        if "llm_model" in update_data and update_data["llm_model"] is not None:
            session["llm_model"] = update_data["llm_model"]
        
        if "mcp_server_id" in update_data and update_data["mcp_server_id"] is not None:
            session["mcp_server_id"] = update_data["mcp_server_id"]
        
        # 更新时间戳
        session["updated_at"] = int(time.time())
        
        # 更新最后活动时间
        session["last_activity"] = int(time.time())
        
        # 保存会话
        await self._save_session(id, session)
        
        return session
    
    async def update_session_activity(self, id: str) -> Dict[str, Any]:
        """更新会话活动时间"""
        session = await self.get_session(id)
        
        if not session:
            raise ValueError(f"会话 {id} 不存在")
        
        # 更新最后活动时间
        session["last_activity"] = int(time.time())
        
        # 如果会话已超时，移除超时标志
        if session.get('timed_out'):
            del session['timed_out']
            logger.debug(f"会话 {id} 重新激活")
        
        # 保存会话
        await self._save_session(id, session)
        
        return session
    
    async def delete_session(self, id: str) -> bool:
        """删除会话"""
        session_path = os.path.join(SESSION_DIR, f"{id}.json")
        
        if not os.path.exists(session_path):
            return False
        
        try:
            os.remove(session_path)
            return True
        except Exception as e:
            logger.error(f"删除会话 {id} 失败: {str(e)}")
            return False

    async def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的所有消息"""
        session = await self.get_session(session_id)
        
        if not session:
            raise ValueError(f"会话 {session_id} 不存在")
        
        return session.get("messages", [])
    
    async def add_message(self, session_id: str, role: str, content: Any, tool_call_id: Optional[str] = None) -> Dict[str, Any]:
        """添加消息到会话"""
        session = await self.get_session(session_id)
        
        if not session:
            raise ValueError(f"会话 {session_id} 不存在")
        
        # 检查会话是否超时
        if session.get('timed_out'):
            raise ValueError(f"会话 {session_id} 已超时，无法添加消息")
        
        # 处理content格式
        if not isinstance(content, dict) and role == 'user':
            content = {
                "type": "text",
                "text": str(content)
            }
        
        # 创建消息
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": int(time.time())
        }
        
        # 如果提供了tool_call_id，添加到消息中
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        
        # 添加到会话消息列表
        if "messages" not in session:
            session["messages"] = []
        
        session["messages"].append(message)
        
        # 更新会话时间戳
        session["updated_at"] = int(time.time())
        
        # 更新最后活动时间
        session["last_activity"] = int(time.time())
        
        # 保存会话
        await self._save_session(session_id, session)
        
        return message
    
    async def clear_messages(self, session_id: str) -> bool:
        """清空会话消息"""
        session = await self.get_session(session_id)
        
        if not session:
            raise ValueError(f"会话 {session_id} 不存在")
        
        # 检查会话是否超时
        if session.get('timed_out'):
            raise ValueError(f"会话 {session_id} 已超时，无法清空消息")
        
        # 清空消息
        session["messages"] = []
        
        # 更新时间戳
        session["updated_at"] = int(time.time())
        
        # 更新最后活动时间
        session["last_activity"] = int(time.time())
        
        # 保存会话
        await self._save_session(session_id, session)
        
        return True
    
    async def _save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """保存会话到文件"""
        # 确保会话目录存在
        if not os.path.exists(SESSION_DIR):
            logger.info(f"创建会话目录: {SESSION_DIR}")
            os.makedirs(SESSION_DIR, exist_ok=True)
            
        session_path = os.path.join(SESSION_DIR, f"{session_id}.json")
        
        try:
            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"会话 {session_id} 已保存")
        except Exception as e:
            logger.error(f"保存会话 {session_id} 失败: {str(e)}")
            raise e
    
    async def _check_session_timeout(self, session: Dict[str, Any]) -> None:
        """检查会话是否超时，如果超时则添加超时标记"""
        if not session:
            return
        
        # 如果会话不包含last_activity字段，初始化它
        if "last_activity" not in session:
            session["last_activity"] = int(time.time())
            if "id" in session:
                await self._save_session(session["id"], session)
            return
        
        # 获取最后活动时间和当前时间
        last_activity = session.get("last_activity", 0)
        current_time = int(time.time())
        
        # 计算是否超时
        if (current_time - last_activity) > self.timeout_seconds:
            # 会话已超时，添加超时标记
            if not session.get("timed_out"):
                session["timed_out"] = True
                session_id = session.get("id")
                logger.info(f"会话 {session_id} 已超时，上次活动: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_activity))}")
                
                # 保存会话状态
                if session_id:
                    await self._save_session(session_id, session)
        else:
            # 会话未超时，确保没有超时标记
            if session.get("timed_out"):
                del session["timed_out"]
                session_id = session.get("id")
                logger.debug(f"会话 {session_id} 超时状态已清除")
                
                # 保存会话状态
                if session_id:
                    await self._save_session(session_id, session)
    
    # 以下方法用于辅助LLM处理
    
    def get_llm_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将消息转换为LLM API消息格式"""
        llm_messages = []
        
        for message in messages:
            try:
                role = message["role"]
                
                # 处理不同角色的消息
                if role == "user":
                    llm_messages.append({
                        "role": "user",
                        "content": message["content"]["text"] if isinstance(message["content"], dict) and "text" in message["content"] else message["content"]
                    })
                elif role == "assistant":
                    # 检查是否有工具调用
                    if message.get("toolCalls") or message.get("tool_calls"):
                        tool_calls = message.get("toolCalls") or message.get("tool_calls") or []
                        
                        assistant_msg = {
                            "role": "assistant",
                            "content": message["content"]["text"] if isinstance(message["content"], dict) and "text" in message["content"] else message["content"],
                        }
                        
                        # 添加tool_calls字段
                        if tool_calls:
                            assistant_msg["tool_calls"] = tool_calls
                            
                            # 如果内容为空且有工具调用，根据规范将content设为null
                            if not assistant_msg["content"]:
                                assistant_msg["content"] = None
                        
                        llm_messages.append(assistant_msg)
                    else:
                        llm_messages.append({
                            "role": "assistant",
                            "content": message["content"]["text"] if isinstance(message["content"], dict) and "text" in message["content"] else message["content"]
                        })
                elif role == "tool":
                    # 确保包含tool_call_id
                    tool_call_id = message.get("tool_call_id") or message.get("toolCallId")
                    if not tool_call_id:
                        logger.warning(f"工具消息缺少tool_call_id，将使用默认值: {message}")
                        tool_call_id = "unknown_call"
                    
                    llm_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": message["content"]["text"] if isinstance(message["content"], dict) and "text" in message["content"] else message["content"]
                    })
            except Exception as e:
                logger.error(f"处理消息时出错: {str(e)}, 消息: {message}")
                continue
        
        # 添加调试日志
        logger.debug(f"转换后的LLM消息格式: {json.dumps(llm_messages, ensure_ascii=False, indent=2)}")
        return llm_messages

# 创建全局会话管理器实例，向后兼容
session_manager = SessionService() 