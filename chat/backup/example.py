#!/usr/bin/env python3
"""
Example usage of the chat package.
"""

import asyncio
import logging
from chat import ChatManager, ChatConfig, BedrockConfig, MCPConfig, KnowledgeBaseConfig

# Configure logging
logging.basicConfig(level=logging.INFO)


async def example_chat():
    """Example of using the ChatManager programmatically."""
    
    # Create custom configuration
    config = ChatConfig(
        bedrock=BedrockConfig(
            default_model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            temperature=0.7,
            max_tokens=4096
        ),
        mcp=MCPConfig(
            command="npx",
            args=["-y", "@baidumap/mcp-server-baidu-map"]
        ),
        knowledge_base=KnowledgeBaseConfig(
            knowledge_base_id='R0LR957R1P'
        )
    )
    
    # Use ChatManager as async context manager
    async with ChatManager(config) as chat_manager:
        print("Chat manager initialized successfully!")
        
        # Example conversation
        test_messages = [
            "你好，请介绍一下你自己",
            "北京的天气怎么样？",
            "帮我查找一下附近的餐厅"
        ]
        
        for message in test_messages:
            print(f"\n用户: {message}")
            print("正在思考...")
            
            try:
                response = await chat_manager.process_message(message)
                
                print(f"助手: {response['text']}")
                print(f"Token使用: {response['usage']}")
                
            except Exception as e:
                print(f"错误: {str(e)}")
        
        # Show conversation history
        print(f"\n对话历史包含 {chat_manager.get_message_count()} 条消息")


async def example_simple_usage():
    """Simple usage example with default configuration."""
    
    async with ChatManager() as chat_manager:
        response = await chat_manager.process_message("你好！")
        print(f"回复: {response['text']}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_chat())