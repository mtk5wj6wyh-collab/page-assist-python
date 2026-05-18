"""
MCP协议服务
Model Context Protocol支持
"""
import asyncio
import json
import subprocess
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import httpx


class ServerType(Enum):
    """MCP服务器类型"""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


class AuthType(Enum):
    """认证类型"""
    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"


@dataclass
class MCPTool:
    """MCP工具"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_id: str


@dataclass
class MCPServer:
    """MCP服务器"""
    id: str
    name: str
    server_type: ServerType
    command: Optional[str] = None
    args: List[str] = None
    env: Dict[str, str] = None
    url: Optional[str] = None
    headers: Dict[str, str] = None
    auth_type: AuthType = AuthType.NONE
    auth_config: Dict[str, str] = None
    is_enabled: bool = True
    tools: List[MCPTool] = None
    
    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.env is None:
            self.env = {}
        if self.headers is None:
            self.headers = {}
        if self.auth_config is None:
            self.auth_config = {}
        if self.tools is None:
            self.tools = []


class MCPProtocolHandler:
    """MCP协议处理器"""
    
    @staticmethod
    async def initialize_request(server: MCPServer) -> Dict[str, Any]:
        """生成初始化请求"""
        return {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "page-assist",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
    
    @staticmethod
    async def tools_list_request() -> Dict[str, Any]:
        """生成工具列表请求"""
        return {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
    
    @staticmethod
    async def tools_call_request(
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成工具调用请求"""
        return {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": 3
        }


class MCPServerProcess:
    """MCP服务器进程管理"""
    
    def __init__(self, server: MCPServer):
        self.server = server
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.pending_requests: Dict[int, asyncio.Future] = {}
    
    async def start(self):
        """启动服务器进程"""
        if self.server.server_type != ServerType.STDIO:
            return
        
        if not self.server.command:
            raise ValueError("No command specified for STDIO server")
        
        self.process = subprocess.Popen(
            [self.server.command] + self.server.args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**subprocess.os.environ, **self.server.env},
            text=True
        )
    
    async def stop(self):
        """停止服务器进程"""
        if self.process:
            self.process.terminate()
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
    
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求并等待响应"""
        if not self.process:
            raise RuntimeError("Server process not started")
        
        self.request_id += 1
        request["id"] = self.request_id
        
        future = asyncio.Future()
        self.pending_requests[self.request_id] = future
        
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json)
        self.process.stdin.flush()
        
        return await asyncio.wait_for(future, timeout=60.0)
    
    async def read_response(self) -> Optional[Dict[str, Any]]:
        """读取响应"""
        if not self.process:
            return None
        
        line = self.process.stdout.readline()
        if line:
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                return None
        return None


class MCPService:
    """MCP服务管理器"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self.server_processes: Dict[str, MCPServerProcess] = {}
        self.client = httpx.AsyncClient(timeout=60.0)
    
    def add_server(self, server: MCPServer):
        """添加MCP服务器"""
        self.servers[server.id] = server
    
    def remove_server(self, server_id: str):
        """移除MCP服务器"""
        if server_id in self.server_processes:
            asyncio.create_task(self.server_processes[server_id].stop())
            del self.server_processes[server_id]
        if server_id in self.servers:
            del self.servers[server_id]
    
    async def start_server(self, server_id: str) -> bool:
        """启动服务器"""
        server = self.servers.get(server_id)
        if not server:
            return False
        
        if server.server_type == ServerType.STDIO:
            process = MCPServerProcess(server)
            await process.start()
            self.server_processes[server_id] = process
            
            # 初始化
            init_request = await MCPProtocolHandler.initialize_request(server)
            await process.send_request(init_request)
            
            # 获取工具列表
            tools_request = await MCPProtocolHandler.tools_list_request()
            response = await process.send_request(tools_request)
            
            if "result" in response and "tools" in response["result"]:
                server.tools = [
                    MCPTool(
                        name=t["name"],
                        description=t["description"],
                        input_schema=t.get("inputSchema", {}),
                        server_id=server_id
                    )
                    for t in response["result"]["tools"]
                ]
            
            return True
        
        elif server.server_type in [ServerType.SSE, ServerType.HTTP]:
            # SSE/HTTP服务器不需要本地进程
            return True
        
        return False
    
    async def stop_server(self, server_id: str):
        """停止服务器"""
        if server_id in self.server_processes:
            await self.server_processes[server_id].stop()
            del self.server_processes[server_id]
    
    async def call_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用MCP工具"""
        server = self.servers.get(server_id)
        if not server:
            raise ValueError(f"Server {server_id} not found")
        
        if server.server_type == ServerType.STDIO:
            process = self.server_processes.get(server_id)
            if not process:
                await self.start_server(server_id)
                process = self.server_processes[server_id]
            
            request = await MCPProtocolHandler.tools_call_request(tool_name, arguments)
            response = await process.send_request(request)
            
            if "result" in response:
                return response["result"]
            elif "error" in response:
                raise Exception(response["error"])
            return {}
        
        elif server.server_type in [ServerType.SSE, ServerType.HTTP]:
            headers = server.headers.copy()
            
            if server.auth_type == AuthType.API_KEY:
                key_name = server.auth_config.get("key_name", "X-API-Key")
                headers[key_name] = server.auth_config.get("api_key", "")
            
            response = await self.client.post(
                server.url,
                json={"method": "tools/call", "params": {"name": tool_name, "arguments": arguments}},
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        
        return {}
    
    def get_tools(self, server_id: Optional[str] = None) -> List[MCPTool]:
        """获取工具列表"""
        if server_id:
            server = self.servers.get(server_id)
            return server.tools if server else []
        
        tools = []
        for server in self.servers.values():
            tools.extend(server.tools)
        return tools
    
    async def close(self):
        """关闭所有连接"""
        for server_id in list(self.server_processes.keys()):
            await self.stop_server(server_id)
        await self.client.aclose()


# 全局MCP服务实例
mcp_service = MCPService()
