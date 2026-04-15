#!/usr/bin/env python3
"""
交互式MQ测试脚本 - 支持终端输入
"""

import sys
import time
import uuid

# 添加common路径
sys.path.append('../../common')

try:
    from rabbitmq import RabbitMQ
    print("✅ MQ模块导入成功")
except ImportError as e:
    print(f"❌ MQ模块导入失败: {e}")
    sys.exit(1)

def interactive_test():
    """交互式测试 - 从终端输入内容"""
    mq = RabbitMQ()
    
    print("\n" + "="*60)
    print("🎯 交互式MQ测试工具")
    print("="*60)
    print("💡 提示：")
    print("  - 输入 'quit' 或 'exit' 退出")
    print("  - 输入 'new' 开始新会话（新通道号）")
    print("  - 输入 'hangup' 发送挂断消息")
    print("  - 直接输入文本作为ASR内容发送")
    print("="*60 + "\n")
    
    channel_id = "C0"  # 默认通道号
    caller_number = "13800138000"
    user_circuit = "1001"
    session_count = 0
    
    while True:
        try:
            # 获取用户输入
            user_input = input(f"[通道{channel_id}] 请输入ASR内容: ").strip()
            
            # 处理特殊命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 退出测试工具")
                break
            
            if user_input.lower() == 'new':
                session_count += 1
                channel_id = f"C{session_count}"
                print(f"✨ 开始新会话，通道号: {channel_id}")
                continue
            
            if user_input.lower() == 'hangup':
                # 发送挂断消息
                hangup_message = f"HANGUP:CHANNEL={channel_id}"
                print(f"📤 发送挂断: {hangup_message}")
                try:
                    mq.publish(hangup_message)
                    print("✅ 挂断消息发送成功")
                except Exception as e:
                    print(f"❌ 发送失败: {e}")
                continue
            
            if not user_input:
                print("⚠️  输入不能为空")
                continue
            
            # 生成ASR消息
            request_id = str(uuid.uuid4())[:8]
            filename = f"test_{int(time.time())}.wav"
            
            message = (
                f"ASR_MSG:"
                f"CHANNEL={channel_id}:"
                f"SEQ={request_id}:"
                f"FILE={filename}:"
                f"UNIT=:"
                f"PERSONNEL=:"
                f"SURNAME=:"
                f"POST=:"
                f"PHONE={caller_number}:"
                f"ASRCONTENT={user_input}:"
                f"USERCIRCUIT={user_circuit}"
            )
            
            print(f"📤 发送: {message}")
            
            try:
                mq.publish(message)
                print("✅ 发送成功\n")
            except Exception as e:
                print(f"❌ 发送失败: {e}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 收到中断信号，退出测试工具")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            continue

def batch_test():
    """批量测试 - 预设测试用例"""
    mq = RabbitMQ()
    
    print("\n" + "="*60)
    print("🧪 批量测试模式")
    print("="*60 + "\n")
    
    # 预设测试用例
    test_cases = [
        {
            "description": "测试1：查询张三",
            "asr_content": "查一下张三",
            "channel_id": "C0"
        },
        {
            "description": "测试2：追问其他电话",
            "asr_content": "还有其他电话吗",
            "channel_id": "C0"
        },
        {
            "description": "测试3：追问手机号",
            "asr_content": "他的手机是多少",
            "channel_id": "C0"
        },
        {
            "description": "测试4：挂断",
            "asr_content": "HANGUP",
            "channel_id": "C0"
        }
    ]
    
    caller_number = "13800138000"
    user_circuit = "1001"
    
    for i, test_case in enumerate(test_cases):
        print(f"\n🧪 {test_case['description']}")
        print(f"📝 ASR内容: {test_case['asr_content']}")
        print(f"🔗 通道号: {test_case['channel_id']}")
        
        if test_case['asr_content'] == "HANGUP":
            # 发送挂断消息
            message = f"HANGUP:CHANNEL={test_case['channel_id']}"
        else:
            # 生成ASR消息
            request_id = str(uuid.uuid4())[:8]
            filename = f"test_{int(time.time())}.wav"
            
            message = (
                f"ASR_MSG:"
                f"CHANNEL={test_case['channel_id']}:"
                f"SEQ={request_id}:"
                f"FILE={filename}:"
                f"UNIT=:"
                f"PERSONNEL=:"
                f"SURNAME=:"
                f"POST=:"
                f"PHONE={caller_number}:"
                f"ASRCONTENT={test_case['asr_content']}:"
                f"USERCIRCUIT={user_circuit}"
            )
        
        print(f"📤 发送: {message}")
        
        try:
            mq.publish(message)
            print("✅ 发送成功")
        except Exception as e:
            print(f"❌ 发送失败: {e}")
        
        # 等待处理
        if i < len(test_cases) - 1:
            print("⏳ 等待3秒...")
            time.sleep(3)
    
    print("\n🎉 批量测试完成！")

if __name__ == "__main__":
    print("\n选择测试模式:")
    print("1. 交互式测试（从终端输入）")
    print("2. 批量测试（预设用例）")
    
    choice = input("\n请输入选择 (1/2): ").strip()
    
    if choice == "1":
        interactive_test()
    elif choice == "2":
        batch_test()
    else:
        print("无效选择，启动交互式测试")
        interactive_test()
