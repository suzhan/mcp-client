import os
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from app.services.session_service import SessionService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"]
)

class SessionCreate(BaseModel):
    title: str = "New Chat"
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    mcp_server_id: Optional[str] = None

class SessionUpdate(BaseModel):
    title: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    mcp_server_id: Optional[str] = None

class MessageCreate(BaseModel):
    session_id: str
    role: str
    content: Dict[str, Any]
    tool_call_id: Optional[str] = None

@router.get("/")
async def get_sessions():
    try:
        session_service = SessionService()
        return {"sessions": await session_service.get_sessions()}
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")

@router.post("/")
async def create_session(session: SessionCreate):
    try:
        session_service = SessionService()
        created_session = await session_service.create_session(
            title=session.title,
            llm_provider=session.llm_provider,
            llm_model=session.llm_model,
            mcp_server_id=session.mcp_server_id
        )
        return created_session
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")

@router.get("/{session_id}")
async def get_session(session_id: str):
    try:
        session_service = SessionService()
        session = await session_service.get_session(session_id)
        
        # 检查会话是否超时
        if session.get('last_activity'):
            last_activity = session.get('last_activity')
            logger.debug(f"会话 {session_id} 最后活动时间: {last_activity}")
            
            # 检查是否已启用超时设置
            if hasattr(settings, 'SESSION_TIMEOUT_SECONDS') and settings.SESSION_TIMEOUT_SECONDS > 0:
                import time
                current_time = int(time.time())
                elapsed = current_time - last_activity
                logger.debug(f"会话 {session_id} 已过去 {elapsed} 秒 (超时设置: {settings.SESSION_TIMEOUT_SECONDS} 秒)")
                
                if elapsed > settings.SESSION_TIMEOUT_SECONDS:
                    logger.warning(f"会话 {session_id} 已超时 ({elapsed} 秒)")
                    # 添加超时标志到会话数据
                    session['timed_out'] = True
        
        if not session:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        return session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取会话失败: {str(e)}")

@router.put("/{session_id}")
async def update_session(session_id: str, session_update: SessionUpdate):
    try:
        session_service = SessionService()
        
        # 首先获取会话检查是否超时
        current_session = await session_service.get_session(session_id)
        if current_session.get('timed_out'):
            logger.warning(f"会话 {session_id} 已超时，无法更新")
            raise HTTPException(status_code=400, detail=f"会话已超时，请刷新页面或创建新会话")
        
        # 更新会话状态和最后活动时间
        updated_session = await session_service.update_session(
            id=session_id,
            title=session_update.title,
            llm_provider=session_update.llm_provider,
            llm_model=session_update.llm_model,
            mcp_server_id=session_update.mcp_server_id
        )
        return updated_session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新会话失败: {str(e)}")

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    try:
        session_service = SessionService()
        result = await session_service.delete_session(session_id)
        return {"success": result}
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")

@router.get("/{session_id}/messages")
async def get_messages(session_id: str):
    try:
        session_service = SessionService()
        
        # 首先获取会话检查是否超时
        current_session = await session_service.get_session(session_id)
        
        # 如果会话未超时，更新最后活动时间
        if not current_session.get('timed_out'):
            await session_service.update_session_activity(session_id)
        
        messages = await session_service.get_messages(session_id)
        return {"messages": messages}
    except Exception as e:
        logger.error(f"获取会话消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取会话消息失败: {str(e)}")

@router.post("/message")
async def add_message(message: MessageCreate):
    try:
        session_service = SessionService()
        
        # 首先获取会话检查是否超时
        current_session = await session_service.get_session(message.session_id)
        if current_session.get('timed_out'):
            logger.warning(f"会话 {message.session_id} 已超时，无法添加消息")
            raise HTTPException(status_code=400, detail=f"会话已超时，请刷新页面或创建新会话")
        
        # 更新会话最后活动时间
        await session_service.update_session_activity(message.session_id)
        
        created_message = await session_service.add_message(
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            tool_call_id=message.tool_call_id
        )
        return created_message
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加消息失败: {str(e)}")

@router.post("/{session_id}/clear-messages")
async def clear_messages(session_id: str):
    try:
        session_service = SessionService()
        
        # 首先获取会话检查是否超时
        current_session = await session_service.get_session(session_id)
        if current_session.get('timed_out'):
            logger.warning(f"会话 {session_id} 已超时，无法清除消息")
            raise HTTPException(status_code=400, detail=f"会话已超时，请刷新页面或创建新会话")
        
        # 更新会话最后活动时间
        await session_service.update_session_activity(session_id)
        
        result = await session_service.clear_messages(session_id)
        return {"success": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清空会话消息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空会话消息失败: {str(e)}") 