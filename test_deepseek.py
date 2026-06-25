#!/usr/bin/env python
"""
DeepSeek配置测试脚本
"""
import os
import sys
import django
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 初始化Django
django.setup()

def test_deepseek_config():
    """测试DeepSeek配置"""
    print("🧪 测试DeepSeek配置...")
    
    from django.conf import settings
    
    # 检查配置
    print(f"✅ DEEPSEEK_API_KEY: {'已配置' if settings.DEEPSEEK_API_KEY else '未配置'}")
    print(f"✅ DEEPSEEK_BASE_URL: {settings.DEEPSEEK_BASE_URL}")
    print(f"✅ DEFAULT_LLM_PROVIDER: {settings.DEFAULT_LLM_PROVIDER}")
    print(f"✅ DEFAULT_LLM_MODEL: {settings.DEFAULT_LLM_MODEL}")
    
    if not settings.DEEPSEEK_API_KEY:
        print("⚠️  警告：DEEPSEEK_API_KEY未配置，请在.env文件中添加")
        return False
    
    return True

def test_deepseek_client():
    """测试DeepSeek客户端"""
    print("\n🧪 测试DeepSeek客户端...")
    
    try:
        from apps.model_management.deepseek_client import DeepSeekClient, DeepSeekMessage
        
        client = DeepSeekClient()
        print("✅ DeepSeek客户端初始化成功")
        
        # 测试简单对话
        messages = [
            DeepSeekMessage(role='user', content='你好，请简单介绍一下你自己')
        ]
        
        print("🔄 发送测试消息...")
        response = client.chat_completion(
            messages=messages,
            model='deepseek-chat',
            temperature=0.7,
            max_tokens=100
        )
        
        print("✅ DeepSeek API调用成功")
        print(f"📝 回复内容: {response.choices[0]['message']['content']}")
        
        return True
        
    except Exception as e:
        print(f"❌ DeepSeek客户端测试失败: {str(e)}")
        return False

def test_ai_service():
    """测试AI服务"""
    print("\n🧪 测试AI服务...")
    
    try:
        from apps.model_management.ai_service import AIServiceFactory
        
        # 获取DeepSeek服务
        service = AIServiceFactory.get_service('deepseek')
        print("✅ AI服务工厂初始化成功")
        
        # 测试生成回复
        print("🔄 测试生成回复...")
        response = service.generate_response(
            prompt="请简单介绍一下DeepSeek",
            temperature=0.7,
            max_tokens=100
        )
        
        print("✅ AI服务回复生成成功")
        print(f"📝 回复内容: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI服务测试失败: {str(e)}")
        return False

def test_fallback_to_openai():
    """测试回退到OpenAI"""
    print("\n🧪 测试回退到OpenAI...")
    
    try:
        from apps.model_management.ai_service import AIServiceFactory
        
        # 获取OpenAI服务
        service = AIServiceFactory.get_service('openai')
        print("✅ OpenAI服务初始化成功")
        
        # 简单测试（如果配置了OpenAI）
        from django.conf import settings
        if settings.OPENAI_API_KEY:
            print("🔄 测试OpenAI回复...")
            response = service.generate_response(
                prompt="Hello, please introduce yourself briefly",
                temperature=0.7,
                max_tokens=50
            )
            print("✅ OpenAI服务回复生成成功")
            print(f"📝 回复内容: {response}")
        else:
            print("⚠️  OpenAI API密钥未配置，跳过测试")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenAI服务测试失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🚀 开始测试ManxiAI的DeepSeek配置")
    print("=" * 50)
    
    tests = [
        ("配置检查", test_deepseek_config),
        ("DeepSeek客户端", test_deepseek_client),
        ("AI服务", test_ai_service),
        ("OpenAI回退", test_fallback_to_openai),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                failed += 1
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} 测试异常: {str(e)}")
        
        print("-" * 30)
    
    print(f"\n📊 测试结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 所有测试通过！DeepSeek配置正确。")
    else:
        print("⚠️  部分测试失败，请检查配置和网络连接。")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 