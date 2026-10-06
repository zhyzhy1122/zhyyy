import os
os.chdir('/app')
import uuid

from services.agent_service import ask_agent_stream

sid = f"debug_{uuid.uuid4().hex[:8]}"
questions = [
    "宠物店有什么洗护服务",
    "你能看到我上传的AI工程师路线文档吗",
]

for q in questions:
    print("\n" + "#" * 70)
    print(f"【问题】{q}")
    print("#" * 70)
    out = ""
    try:
        for chunk in ask_agent_stream(q, sid):
            out += chunk
        print(f"【AI答复】{out}")
    except Exception as e:
        print(f"【异常】{type(e).__name__}: {e}")
    print()