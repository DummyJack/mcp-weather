import json
import httpx
from typing import Any
from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服務器
mcp = FastMCP("WeahterServer")

# OpenWeather API 配置
OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5/weather"
API_KEY = "5fd4b790920c0ecbf91ef6f1bcbe25ae"
USER_AGENT = "weather-app/1.0"

async def get_weather(city: str) -> dict[str, Any] | None:
    """
    從 OpenWeather API 獲取天氣資訊
    :param city: 城市名稱(英文, 例如: Taipei)
    :return: 天氣資料字典，若出錯返回包含 error 資訊的字典
    """
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "zh_tw",
    }
    headers = {
        "User-Agent": USER_AGENT,
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(OPENWEATHER_BASE, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json() # 返回字典類型
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"An error occurred: {str(e)}"}
 
def format_weather(data: dict[str, Any] | str) -> str:
    """
    格式化天氣資料
    :param data: 天氣資料(可以是字典或 JSON 字符串)
    :return: 格式化後的天氣資訊字符串
    """
    # 如果傳入的是字符串，則先轉換為字典
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            return f"無法解析天氣資料: {e}"

    # 如果資料中包含錯誤資訊，直接返回錯誤提示
    if "error" in data:
        return f"{data['error']}"   
    
    city = data.get("name", "未知")
    country = data.get("sys", {}).get("country", "未知")
    temp = data.get("main", {}).get("temp", "N/A")
    humidity = data.get("main", {}).get("humidity", "N/A")
    wind_speed = data.get("wind", {}).get("speed", "未知")
    # weather 可能為空列表，因此用 [0] 前先提供默認字典
    weather_list = data.get("weather", [{}])
    description = weather_list[0].get("description", "未知")

    return (
        f"{city}, {country}\n"
        f"溫度: {temp}°C\n"
        f"濕度: {humidity}%\n"
        f"風速: {wind_speed} m/s\n"
        f"天氣: {description}\n"
    )

# 指令: 註冊為 MCP 工具(可被客戶端呼叫)
@mcp.tool()
async def query_weather(city: str) -> str:
    """
    輸入指定的英文名稱，返回今日天氣查詢結果
    :param city: 城市名稱(英文)
    :return: 格式化後的天氣資訊
    """
    data = await get_weather(city)
    return format_weather(data)

if __name__ == "__main__":
    # 以標準 I/O 方法運行 MCP 服務器
    mcp.run(transport="stdio")