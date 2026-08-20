import asyncio
# 导入 asyncio：用来跑 async 的 MCP 加载流（get_tools 是协程）
import os
import shutil
import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor
# 线程池：把 async 调用扔到独立线程里跑，避开"已在事件循环里再跑 asyncio.run"的冲突
from langchain_mcp_adapters.client import MultiServerMCPClient
# 官方桥接客户端：连 MCP server、取工具
from langchain_core.tools import StructuredTool
# 用 StructuredTool 把 async 工具再包成"能用 .invoke() 同步调用"的 BaseTool


def _resolve_ddg_command() -> str:
    # 内部函数：找到 DuckDuckGo MCP server 的可执行文件路径
    # 返回：可执行的绝对路径字符串（跨平台：Windows 是 .exe，Linux/Docker 是无扩展名脚本）
    found = shutil.which("duckduckgo-mcp-server")
    # 先试 PATH：Windows 下会命中 Scripts\duckduckgo-mcp-server.exe
    if found:
        # 命中就直接用（Docker 里装好后入口在 PATH）
        return found
        # 返回命中路径
    # PATH 找不到时，退而求其次：拼当前环境 Scripts 目录下的 .exe（本地 .venv 常见）
    return os.path.join(sysconfig.get_path("scripts"), "duckduckgo-mcp-server.exe")
    # 返回拼出的绝对路径（不存在则由 MCP 启动时报错，可定位问题）


DDG_CMD = _resolve_ddg_command()
# 模块级常量：启动时解析一次 DDG server 路径，避免每次都算

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
    "ddg": {
        # 服务器名：ddg；接入 DuckDuckGo 搜索（search / fetch_content 工具）
        "command": DDG_CMD,
        # 命令：DuckDuckGo MCP server 的可执行文件（见上方 _resolve_ddg_command）
        "args": [],
        # args: []：必须给空列表，否则 stdio 连接会因缺 args 报错
        "transport": "stdio",
        # 传输方式：stdio=由本进程 fork 出 DDG server 子进程，走管道通信
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

DESCRIPTION_OVERRIDES = {
    # 按工具名覆盖 MCP 原始描述：LLM 靠 description 决定"要不要调、什么时候调"
    # 原始 description 多为英文且偏笼统，这里用中文写清使用边界，避免和知识库工具混淆
    "search": (
        "联网搜索当前/最新的网络信息，返回网页标题、链接和摘要。"
        "使用场景：用户问题涉及实时资讯、市场行情、网上普遍说法、最新动态，"
        "或需要拿网络信息做对比验证（例如『和网上说法有什么不同』『这个价贵不贵』）。"
        "注意：这只是通用网络搜索结果，不代表本店知识库内容；"
        "需要店内服务、价格、养护规范时，请调用 query_knowledge_base。"
    ),
}

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
        description=DESCRIPTION_OVERRIDES.get(astc_tool.name, astc_tool.description),
        # 若本工具在 DESCRIPTION_OVERRIDES 里有中文定制则用它，否则保留原始描述
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