#!/usr/bin/env python
"""
ManxiAI 项目启动脚本
"""
import os
import sys
import django
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    # 设置Django设置模块
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    # 初始化Django
    django.setup()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'migrate':
            # 数据库迁移
            execute_from_command_line(['manage.py', 'makemigrations'])
            execute_from_command_line(['manage.py', 'migrate'])
            print("数据库迁移完成")
            
        elif command == 'createsuperuser':
            # 创建超级用户
            execute_from_command_line(['manage.py', 'createsuperuser'])
            
        elif command == 'runserver':
            # 启动开发服务器
            port = sys.argv[2] if len(sys.argv) > 2 else '8000'
            execute_from_command_line(['manage.py', 'runserver', f'0.0.0.0:{port}'])
            
        elif command == 'celery':
            # 启动Celery worker
            os.system('celery -A config worker --loglevel=info')
            
        elif command == 'shell':
            # 启动Django shell
            execute_from_command_line(['manage.py', 'shell'])
            
        else:
            print(f"未知命令: {command}")
            print("可用命令: migrate, createsuperuser, runserver, celery, shell")
    else:
        print("ManxiAI 项目启动脚本")
        print("使用方法: python start.py <command>")
        print("可用命令:")
        print("  migrate       - 执行数据库迁移")
        print("  createsuperuser - 创建超级用户")
        print("  runserver     - 启动开发服务器")
        print("  celery        - 启动Celery worker")
        print("  shell         - 启动Django shell") 