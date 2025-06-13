## 安裝環境

```bash
pip install uv
uv venv mcp-weather-example
```

## Windows

#### 啟動虛擬環境

```bash
.\mcp-weather-example\Scripts\activate
```

#### 安裝依賴包

```bash
cd mcp-weather
uv add mcp
```

#### 執行

```bash
python mcp-client.py weather-mcp-server.py
```

## Mac

#### 啟動虛擬環境

```bash
source mcp-weather-example/bin/activate
```

#### 安裝依賴包

```bash
cd mcp-weather
uv add mcp
```

#### 執行

```bash
uv run python mcp-client.py weather-mcp-server.py
```
