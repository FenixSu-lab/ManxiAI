#!/usr/bin/env python
"""
测试登录功能的脚本
"""
import requests
import json

def test_login():
    """测试登录功能"""
    print("🧪 测试登录功能...")
    
    # 登录数据
    login_data = {
        "email": "addroc_sue@163.com",
        "password": "123456"
    }
    
    # 发送登录请求
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/auth/users/login/",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 登录成功！")
            print(f"Token: {data.get('token', 'N/A')}")
            print(f"用户信息: {data.get('user', 'N/A')}")
            return True
        else:
            print("❌ 登录失败")
            try:
                error_data = response.json()
                print(f"错误信息: {error_data}")
            except:
                print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False

def test_user_list():
    """测试用户列表接口"""
    print("\n🧪 测试用户列表接口...")
    
    try:
        response = requests.get(
            "http://localhost:8000/api/v1/auth/users/",
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            print("✅ 用户列表获取成功")
            return True
        else:
            print("❌ 用户列表获取失败")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试登录功能")
    print("=" * 50)
    
    # 测试登录
    login_success = test_login()
    
    # 测试用户列表
    user_list_success = test_user_list()
    
    print("\n" + "=" * 50)
    print("📊 测试结果:")
    print(f"登录测试: {'✅ 通过' if login_success else '❌ 失败'}")
    print(f"用户列表测试: {'✅ 通过' if user_list_success else '❌ 失败'}")
    
    if login_success:
        print("\n🎉 登录功能正常！")
    else:
        print("\n⚠️  登录功能存在问题，请检查配置。") 