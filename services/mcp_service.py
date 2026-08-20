import asyncio
# 导入 asyncio：用来跑 async 的 MCP 加载流（get_tools 是协程）
import sys
# 导入 sys：取"当前运行后端的那同一个 python"，确保拉起 mcp-server-fetch 时用的是同一个安装了它的环境
from concurrent.futures import ThreadPoolExecutor
# 线程池：把 async 调用扔到独立线程里跑，避开"已在事件循环里再跑 asyncio.run"的冲突
from langchain_mcp_adapters.client import MultiServerMCPClient
# 官方桥接客户端：连 MCP server、取工具
from langchain_core.tools import StructuredTool
# 用 StructuredTool 把 async 工具再包成"能用 .invoke() 同步调用"的 BaseTool

MCP_SERVERS = {
    # 要接入的 MCP server 注册表：以后加 server 就在这里加一行
    "fetch": {
        # 服务器名：fetch；agent 里工具名前缀会带它
        "command": sys.executable,
        # ★ 关键：用"当前后端同一个 python"当子进程程序，避免 PATH 里别家 python 没装 mcp_server_fetch
        "args": ["-m", "mcp_server_fetch"],
        # 启动参数：python -m mcp_server_fetch 拉起这个 server
        "transport": "stdio",
        # 传输方式：stdio=子进程管道；要加 http 服务器就换成 transport:"http"+url
    },
}

_mcp_tools_cache = None
# 模块级缓存：工具只加载一次（和 _llm 缓存同理），避免每次请求重建 MCP 连接

def _load_raw_tools() -> dict:
    # 内部函数：异步加载所有 server 的原始工具，返回 {server名: [工具们]}
    async def _run():
        # 私有 async 函数：真正的异步加载逻辑
        client = MultiServerMCPClient(connections=MCP_SERVERS)
        # 建客户端（连多个 server，见 MCP_SERVERS）
        loaded = {}
        # 收集结果
        for name in MCP_SERVERS:
            # 遍历要接入的每个 server
            loaded[name] = await client.get_tools(server_name=name)
            # await 取该 server 的工具（async-only 的 StructuredTool）
        return loaded
        # 返回 {server名: [工具]}
    return asyncio.run(_run())
    # 用 asyncio.run 包住 async 流程：一次性把协程跑完拿到结果（只在模块加载时 call 一次）

def _make_sync(astc_tool: StructuredTool) -> StructuredTool:
    # 把一个 async-only 的 MCP 工具，包成可同步 .invoke() 的 StructuredTool
    # 参数 astc_tool：适配器返回的、只能 ainvoke 的原始工具
    # 返回：新的同步 StructuredTool，可直接进 TOOL_MAP
    def _func(**kwargs):
        # 内部函数：给新工具当同步执行体 func 用
        # 参数 kwargs：LLM 给工具的参数字典（由 args_schema 约束）
        with ThreadPoolExecutor(1) as ex:
            # 开一个单线程线程池——新线程里没有正在运行的事件循环，asyncio.run 才合法
            return ex.submit(asyncio.run, astc_tool.ainvoke(kwargs)).result()
            # 在独立线程里跑 asyncio.run( await astc_tool.ainvoke(kwargs) )，拿回结果返回
        # ★ 实测点①：这样包装后的 StructuredTool.invoke() 能否同步拿到结果
    return StructuredTool(
        # 依据原工具的信息再造一个同步工具
        name=astc_tool.name,
        # 同名，agent/LLM 认的是这个名字
        description=astc_tool.description,
        # 同描述，给 LLM 看它干嘛用的
        args_schema=astc_tool.args_schema,
        # 同参数 schema：LLM 按这个结构填参数
        func=_func,
        # 执行体是上面那个 _func（同步）
        # ★ 实测点②：StructuredTool 构造+同步 invoke 是否可用
    )

def get_mcp_tools() -> list[StructuredTool]:
    # 对外主函数：返回一批【可同步调用】的 MCP 工具，供 agent_service 注册进 TOOL_MAP
    global _mcp_tools_cache
    # 访问模块级缓存
    if _mcp_tools_cache is not None:
        # 已加载过
        return _mcp_tools_cache
        # 直接返回缓存
    raw = _load_raw_tools()
    # 加载各 server 的原始(async)工具
    result = []
    # 收集同步工具
    for tools in raw.values():
        # 遍历每个 server 的工具
        for t in tools:
            # 遍历每个工具
            result.append(_make_sync(t))
            # 逐个包成同步版
    _mcp_tools_cache = result
    # 写入缓存
    return result
    # 返回同步工具列表