"""
提示词管理服务
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.prompt import Prompt, CopilotPrompt, PromptModel, CopilotPromptModel


class PromptManager:
    """提示词管理器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========== 自定义提示词 ==========
    
    async def create_prompt(
        self,
        name: str,
        content: str,
        description: str = None,
        tags: List[str] = None,
        category: str = "custom",
        is_default: bool = False,
        is_copilot: bool = False,
        trigger: str = None,
        variables: List[dict] = None
    ) -> Prompt:
        """创建提示词"""
        prompt = Prompt(
            id=str(uuid.uuid4()),
            name=name,
            content=content,
            description=description,
            tags=tags or [],
            category=category,
            is_default=is_default,
            is_copilot=is_copilot,
            trigger=trigger,
            variables=variables or []
        )
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt
    
    async def get_prompt(self, prompt_id: str) -> Optional[Prompt]:
        """获取提示词"""
        result = await self.db.execute(
            select(Prompt).where(Prompt.id == prompt_id)
        )
        return result.scalar_one_or_none()
    
    async def get_prompts(
        self,
        category: str = None,
        tags: List[str] = None,
        include_copilot: bool = True
    ) -> List[Prompt]:
        """获取提示词列表"""
        query = select(Prompt)
        
        if category:
            query = query.where(Prompt.category == category)
        
        if tags:
            # 简单实现：查找包含任一标签的提示词
            for tag in tags:
                query = query.where(Prompt.tags.contains([tag]))
        
        if not include_copilot:
            query = query.where(Prompt.is_copilot == False)
        
        query = query.order_by(Prompt.use_count.desc(), Prompt.name)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_prompt(
        self,
        prompt_id: str,
        name: str = None,
        content: str = None,
        description: str = None,
        tags: List[str] = None,
        is_favorite: bool = None
    ) -> Optional[Prompt]:
        """更新提示词"""
        prompt = await self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        if name is not None:
            prompt.name = name
        if content is not None:
            prompt.content = content
        if description is not None:
            prompt.description = description
        if tags is not None:
            prompt.tags = tags
        if is_favorite is not None:
            prompt.is_favorite = is_favorite
        
        prompt.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt
    
    async def delete_prompt(self, prompt_id: str) -> bool:
        """删除提示词"""
        result = await self.db.execute(
            delete(Prompt).where(Prompt.id == prompt_id)
        )
        await self.db.commit()
        return True
    
    async def increment_use_count(self, prompt_id: str):
        """增加使用计数"""
        prompt = await self.get_prompt(prompt_id)
        if prompt:
            prompt.use_count += 1
            await self.db.commit()
    
    async def render_prompt(
        self,
        prompt_id: str,
        variables: Dict[str, str] = None
    ) -> Optional[str]:
        """渲染提示词（替换变量）"""
        prompt = await self.get_prompt(prompt_id)
        if not prompt:
            return None
        
        content = prompt.content
        variables = variables or {}
        
        # 替换变量
        for var_name, var_value in variables.items():
            content = content.replace(f"{{{{{var_name}}}}}", var_value)
        
        return content
    
    # ========== Copilot提示词 ==========
    
    async def create_copilot_prompt(
        self,
        name: str,
        content: str,
        description: str = None,
        trigger: str = None
    ) -> CopilotPrompt:
        """创建Copilot提示词"""
        prompt = CopilotPrompt(
            id=str(uuid.uuid4()),
            name=name,
            content=content,
            description=description,
            trigger=trigger
        )
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt
    
    async def get_copilot_prompts(self, enabled_only: bool = True) -> List[CopilotPrompt]:
        """获取Copilot提示词"""
        query = select(CopilotPrompt)
        
        if enabled_only:
            query = query.where(CopilotPrompt.is_enabled == True)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_copilot_by_trigger(self, trigger: str) -> Optional[CopilotPrompt]:
        """根据触发词获取Copilot提示词"""
        result = await self.db.execute(
            select(CopilotPrompt)
            .where(CopilotPrompt.trigger == trigger)
            .where(CopilotPrompt.is_enabled == True)
        )
        return result.scalar_one_or_none()
    
    async def update_copilot_prompt(
        self,
        prompt_id: str,
        is_enabled: bool = None
    ) -> Optional[CopilotPrompt]:
        """更新Copilot提示词"""
        result = await self.db.execute(
            select(CopilotPrompt).where(CopilotPrompt.id == prompt_id)
        )
        prompt = result.scalar_one_or_none()
        
        if not prompt:
            return None
        
        if is_enabled is not None:
            prompt.is_enabled = is_enabled
        
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt
    
    async def delete_copilot_prompt(self, prompt_id: str) -> bool:
        """删除Copilot提示词"""
        result = await self.db.execute(
            delete(CopilotPrompt).where(CopilotPrompt.id == prompt_id)
        )
        await self.db.commit()
        return True
    
    # ========== 内置提示词模板 ==========
    
    async def init_builtin_prompts(self):
        """初始化内置提示词"""
        builtin_prompts = [
            {
                "name": "翻译助手",
                "content": "你是一个专业的翻译助手。请将以下内容翻译成{{language}}：\n\n{{content}}",
                "description": "翻译选定或输入的内容",
                "category": "assistant",
                "is_copilot": True,
                "trigger": "翻译",
                "variables": [{"name": "language", "default": "英文"}, {"name": "content", "default": ""}]
            },
            {
                "name": "内容总结",
                "content": "请总结以下内容的主要要点：\n\n{{content}}",
                "description": "总结文本内容",
                "category": "assistant",
                "is_copilot": True,
                "trigger": "总结",
                "variables": [{"name": "content", "default": ""}]
            },
            {
                "name": "代码解释",
                "content": "请解释以下代码的功能和工作原理：\n\n```\n{{code}}\n```",
                "description": "解释代码",
                "category": "programming",
                "is_copilot": True,
                "trigger": "解释代码",
                "variables": [{"name": "code", "default": ""}]
            },
            {
                "name": "语法检查",
                "content": "请检查以下文本的语法错误并给出修改建议：\n\n{{content}}",
                "description": "检查语法",
                "category": "assistant",
                "is_copilot": True,
                "trigger": "语法检查",
                "variables": [{"name": "content", "default": ""}]
            },
        ]
        
        for prompt_data in builtin_prompts:
            existing = await self.get_prompt_by_name(prompt_data["name"])
            if not existing:
                await self.create_prompt(**prompt_data)
    
    async def get_prompt_by_name(self, name: str) -> Optional[Prompt]:
        """根据名称获取提示词"""
        result = await self.db.execute(
            select(Prompt).where(Prompt.name == name)
        )
        return result.scalar_one_or_none()
