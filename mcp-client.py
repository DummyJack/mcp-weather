import asyncio
import os
import json
from typing import Optional
from contextlib import AsyncExitStack

from openai import OpenAI
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 加載 .env
load_dotenv()

class MCPClient:
    # 初始化 MCP 客戶端
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        
        # 檢查 OpenAI API 金鑰
        api_key = os.getenv("OPEN_API_KEY")    
        self.client = OpenAI(api_key=api_key)
        self.session: Optional[ClientSession] = None
    
    async def conect_to_server(self, server_script_path: str):

        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")

        if not(is_python or is_js):
            raise ValueError("服務器腳本必須是 .py or .js 文件")
        
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        # 啟動 MCP 服務器並建立通訊
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # 列出 MCP 服務器上的工具
        response = await self.session.list_tools()
        tools = response.tools
        print("\n已連接到服務器，支持以下工具:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """
        使用 LLM 處理查詢並調用可用的 MCP 工具 (Function Calling)
        """
        messages = [
            {"role": "system", "content": "你是一個智能助手，幫助用戶回答問題。"},
            {"role": "user", "content": query}
        ]
        
        # 獲取 MCP 服務器上的工具列表
        response = await self.session.list_tools()
        # 有效的工具列表 
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
        } for tool in response.tools]

        response = self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            tools=available_tools # 將有效的工具列表給模型
        )

        # 處理返回的內容
        content = response.choices[0]
        print(f"\n\n[Response from model]\n\n{content.message.model_dump()}\n\n")
        if content.finish_reason == "tool_calls":
            # 如何是需要使用工具，就解析工具
            tool_calls = content.message.tool_calls[0]
            tool_name = tool_calls.function.name
            tool_args = json.loads(tool_calls.function.arguments)

            # 執行工具
            result = await self.session.call_tool(tool_name, tool_args)
            print(f"\n\n[Calling tool {tool_name} with args {tool_args}]\n\n")

            # 將模型返回的呼叫工具資料和工具執行結果都存入 messages 中
            messages.append(content.message.model_dump())
            messages.append({
                "role": "tool",
                "content": result.content[0].text,
                "tool_call_id": tool_calls.id
            })

            # 將上面的結果再返回給 LLM 用於生成最終的結果
            response = self.client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
            )
            return response.choices[0].message.content
        return content.message.content
    
    async def chat_loop(self):
        """運行交互聊天循環"""
        print("\n MCP 客戶端已啟動! 輸入 'quit' 退出")
        while True:
            try:
                query = input("\n你: ").strip()
                if query.lower() == "quit":
                    break
                response = await self.process_query(query) # 發送用戶輸入到 OpenAI API 中
                print(f"\n OpenAI: {response}")
            except Exception as e:
                print(f"\n 發生錯誤: {str(e)}")
    
    async def cleanup(self):
        """清理資源"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
    
    client = MCPClient()
    try:
        await client.conect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())