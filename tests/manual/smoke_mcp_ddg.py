# 测试脚本：验证 DuckDuckGo MCP 服务器在加速器下的中文搜索功能
import asyncio
import os
import sysconfig
from concurrent.futures import ThreadPoolExecutor
from langchain_mcp_adapters.client import MultiServerMCPClient

scripts = sysconfig.get_path('scripts')
cmd = os.path.join(scripts, 'duckduckgo-mcp-server.exe')
print('DDG cmd exists:', os.path.exists(cmd), '|', cmd)

conns = {
    'ddg': {
        'command': cmd,
        'args': [],
        'transport': 'stdio',
    }
}


async def load():
    client = MultiServerMCPClient(connections=conns)
    return await client.get_tools(server_name='ddg')


async def inv(tool, kwargs):
    return await tool.ainvoke(kwargs)


if __name__ == '__main__':
    print('loading ddg tools ...')
    tools = asyncio.run(load())
    names = [t.name for t in tools]
    print('TOOLS:', names)
    search = [t for t in tools if t.name == 'search'][0]
    print('--- invoking search ---')
    with ThreadPoolExecutor(1) as ex:
        out = ex.submit(asyncio.run, inv(search, {'query': '宠物猫深度洗护包含什么步骤'})).result()
    text = str(out)
    print('SEARCH_OUT=', text[:400])
    with open(r'd:\python\宠物店rag项目（后续langchain加langgraph）\ddg_out.txt', 'w', encoding='utf-8') as f:
        f.write(text[:2000])