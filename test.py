# test_rag.py（放项目根目录）
from services.rag_service import ask

if __name__ == "__main__":
    while True:
        question = input("请输入你的问题或者输入quit离开：")
        if question == "quit":
            break
        print(ask(question))