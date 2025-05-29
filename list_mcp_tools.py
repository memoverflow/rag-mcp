#!/usr/bin/env python3
"""
最简单的脚本，用于列出 MCP 服务器的工具信息
"""

import asyncio
import json
import sys
import logging
from typing import Dict, List, Any

# 导入已知可用的 MCP 模块
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 设置基本日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def list_mcp_tools():
    """连接 MCP 服务器并列出工具信息"""
    print("正在连接到 MCP 服务器...")
    
    # 服务器配置
    server_params = StdioServerParameters(
        command="uvx",
        args=["awslabs.cost-analysis-mcp-server@latest"],
        env={"AWS_PROFILE": "global"}
    )
    
    try:
        # 创建 stdio 客户端
        stdio_context = stdio_client(server_params)
        read, write = await stdio_context.__aenter__()
        
        # 创建会话
        session_context = ClientSession(read, write)
        session = await session_context.__aenter__()
        
        # 初始化连接
        await session.initialize()
        print("成功连接到 MCP 服务器")
        
        # 获取工具列表
        tools_response = await session.list_tools()
        tools = tools_response.tools
        
        print(f"\n找到 {len(tools)} 个工具:\n")
        
        # 简单输出每个工具的基本信息和JSON表示
        for i, tool in enumerate(tools, 1):
            print(f"===== 工具 {i}: {tool.name} =====")
            print(f"描述: {tool.description}")
            
            # 转换工具对象为字典格式，以便JSON输出
            tool_dict = {
                "name": tool.name,
                "description": tool.description
            }
            
            # 添加参数信息（如果存在）
            if hasattr(tool, 'parameters'):
                tool_dict["parameters"] = tool.parameters
            
            # 添加inputSchema信息（如果存在）
            if hasattr(tool, 'inputSchema'):
                try:
                    # 尝试解析inputSchema为JSON对象
                    tool_dict["inputSchema"] = json.loads(tool.inputSchema)
                except Exception:
                    # 如果解析失败，直接使用原始文本
                    tool_dict["inputSchema"] = tool.inputSchema
            
            # 输出格式化的JSON
            print("\n工具JSON数据:")
            print(json.dumps(tool_dict, indent=2, default=str))
            print("\n" + "-" * 80 + "\n")  # 分隔线
        
        print(f"\n共 {len(tools)} 个工具")
        
        # 关闭连接
        try:
            await session_context.__aexit__(None, None, None)
            await stdio_context.__aexit__(None, None, None)
        except Exception as e:
            print(f"关闭连接出错: {e}")
    
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(list_mcp_tools())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n操作被用户中断")
        sys.exit(130) 