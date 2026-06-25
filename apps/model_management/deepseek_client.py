"""
DeepSeek API客户端
"""
import json
import httpx
from typing import Dict, List, Any, Optional, Iterator
from django.conf import settings
from dataclasses import dataclass, field


@dataclass
class DeepSeekMessage:
    """DeepSeek消息格式"""
    role: str
    content: str


@dataclass
class DeepSeekResponse:
    """DeepSeek响应格式"""
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    # 使用field(default_factory=dict)来处理可能的额外字段
    system_fingerprint: Optional[str] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """处理额外的字段"""
        # 这里可以处理任何额外的字段
        pass


class DeepSeekClient:
    """DeepSeek API客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = base_url or settings.DEEPSEEK_BASE_URL
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            },
            timeout=30.0
        )
    
    def chat_completion(
        self,
        messages: List[DeepSeekMessage],
        model: str = 'deepseek-chat',
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs
    ) -> DeepSeekResponse:
        """
        聊天补全
        """
        data = {
            'model': model,
            'messages': [{'role': msg.role, 'content': msg.content} for msg in messages],
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': stream,
            **kwargs
        }
        
        if stream:
            return self._stream_chat_completion(data)
        else:
            response = self.client.post('/chat/completions', json=data)
            response.raise_for_status()
            response_data = response.json()
            
            # 安全地创建DeepSeekResponse，处理可能的额外字段
            return self._create_response_safely(response_data)
    
    def _create_response_safely(self, response_data: Dict[str, Any]) -> DeepSeekResponse:
        """安全地创建DeepSeekResponse对象"""
        # 提取必需的字段
        required_fields = {
            'id': response_data.get('id', ''),
            'object': response_data.get('object', ''),
            'created': response_data.get('created', 0),
            'model': response_data.get('model', ''),
            'choices': response_data.get('choices', []),
            'usage': response_data.get('usage', {})
        }
        
        # 提取可选字段
        optional_fields = {}
        if 'system_fingerprint' in response_data:
            optional_fields['system_fingerprint'] = response_data['system_fingerprint']
        
        # 提取其他额外字段
        extra_fields = {}
        known_fields = {'id', 'object', 'created', 'model', 'choices', 'usage', 'system_fingerprint'}
        for key, value in response_data.items():
            if key not in known_fields:
                extra_fields[key] = value
        
        if extra_fields:
            optional_fields['extra_fields'] = extra_fields
        
        return DeepSeekResponse(**required_fields, **optional_fields)
    
    def _stream_chat_completion(self, data: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """
        流式聊天补全
        """
        with self.client.stream('POST', '/chat/completions', json=data) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith('data: '):
                    line = line[6:]  # 移除 'data: ' 前缀
                    if line.strip() == '[DONE]':
                        break
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
    
    def embedding(
        self,
        texts: List[str],
        model: str = 'deepseek-embedding',
        **kwargs
    ) -> Dict[str, Any]:
        """
        文本嵌入
        注意：DeepSeek可能不提供embedding服务，这里作为示例
        """
        data = {
            'model': model,
            'input': texts,
            **kwargs
        }
        
        response = self.client.post('/embeddings', json=data)
        response.raise_for_status()
        return response.json()
    
    def get_models(self) -> List[Dict[str, Any]]:
        """
        获取可用模型列表
        """
        response = self.client.get('/models')
        response.raise_for_status()
        return response.json().get('data', [])
    
    def close(self):
        """关闭客户端"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DeepSeekLLMService:
    """DeepSeek LLM服务"""
    
    def __init__(self):
        self.client = DeepSeekClient()
    
    def generate_response(
        self,
        prompt: str,
        context: List[str] = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> str:
        """
        生成回复
        """
        messages = []
        
        # 添加系统消息
        messages.append(DeepSeekMessage(
            role='system',
            content='你是一个有用的AI助手，请根据提供的上下文信息回答用户问题。'
        ))
        
        # 添加上下文信息
        if context:
            context_text = '\n'.join(context)
            messages.append(DeepSeekMessage(
                role='system',
                content=f'相关上下文信息：\n{context_text}'
            ))
        
        # 添加用户问题
        messages.append(DeepSeekMessage(
            role='user',
            content=prompt
        ))
        
        model = model or settings.DEFAULT_LLM_MODEL
        
        try:
            if stream:
                return self._generate_stream_response(messages, model, temperature, max_tokens)
            else:
                response = self.client.chat_completion(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0]['message']['content']
        except Exception as e:
            print(f"DeepSeek API调用详细错误: {str(e)}")
            raise e
    
    def _generate_stream_response(
        self,
        messages: List[DeepSeekMessage],
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Iterator[str]:
        """
        生成流式回复
        """
        for chunk in self.client.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        ):
            if 'choices' in chunk and chunk['choices']:
                delta = chunk['choices'][0].get('delta', {})
                if 'content' in delta:
                    yield delta['content']
    
    def chat_with_history(
        self,
        message: str,
        history: List[Dict[str, str]] = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        带历史记录的对话
        """
        messages = []
        
        # 添加系统消息
        messages.append(DeepSeekMessage(
            role='system',
            content='你是一个有用的AI助手。'
        ))
        
        # 添加历史对话
        if history:
            for item in history:
                messages.append(DeepSeekMessage(
                    role='user',
                    content=item.get('user', '')
                ))
                messages.append(DeepSeekMessage(
                    role='assistant',
                    content=item.get('assistant', '')
                ))
        
        # 添加当前消息
        messages.append(DeepSeekMessage(
            role='user',
            content=message
        ))
        
        model = model or settings.DEFAULT_LLM_MODEL
        
        try:
            response = self.client.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0]['message']['content']
        except Exception as e:
            print(f"DeepSeek对话API调用详细错误: {str(e)}")
            raise e


# 全局实例
deepseek_service = DeepSeekLLMService() 