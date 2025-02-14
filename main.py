import tkinter as tk
from tkinter import scrolledtext
from openai import OpenAI
import threading

file_name = 'api_key.txt'

try:
    with open(file_name, 'r', encoding='utf-8') as file:  # 'r' 表示读取模式
        content = file.read()  # 读取整个文件内容
        print(content)  # 打印文件内容
except FileNotFoundError:
    print(f"文件 '{file_name}' 未找到。")
except Exception as e:
    print(f"发生错误: {e}")

# 初始化 OpenAI 客户端
client = OpenAI(api_key=content, base_url='https://api.deepseek.com')

# 创建主窗口
class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek Chat")
        self.root.geometry("600x400")

        # 创建聊天记录显示区域
        self.chat_history = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled')
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建用户输入框
        self.user_input = tk.Entry(root, font=("Arial", 12))
        self.user_input.pack(fill=tk.X, padx=10, pady=10)
        self.user_input.bind("<Return>", self.send_message)  # 绑定回车键发送消息

        # 创建发送按钮
        self.send_button = tk.Button(root, text="发送", font=("Arial", 12), command=self.send_message)
        self.send_button.pack(pady=5)

        # 初始化消息列表
        self.messages = []

        # 初始化标记
        self.thinking_start = None
        self.thinking_end = None
        self.response_start = None
        self.response_end = None

        # 初始化请求状态
        self.is_request_in_progress = False

        # 初始化缓冲区
        self.thinking_buffer = ""
        self.response_buffer = ""

    # 发送消息
    def send_message(self, event=None):
        if self.is_request_in_progress:
            self.display_message("系统", "请等待当前请求完成后再发送消息。")
            return  # 如果当前有请求正在进行，则不允许发送新消息

        user_input = self.user_input.get().strip()
        if not user_input:
            return  # 如果输入为空，则不处理

        # 显示用户输入
        self.display_message("你", user_input)
        self.user_input.delete(0, tk.END)  # 清空输入框

        # 将用户输入添加到消息列表
        self.messages.append({"role": "user", "content": user_input})

        # 清空缓冲区
        self.thinking_buffer = ""
        self.response_buffer = ""

        # 禁用发送按钮和输入框
        self.set_input_state(disabled=True)

        # 在单独的线程中调用 API 获取回复
        threading.Thread(target=self.get_response, daemon=True).start()

    # 获取 API 回复
    def get_response(self):
        # 标记请求正在进行中
        self.is_request_in_progress = True

        # 显示“正在思考”提示
        self.display_message("DeepSeek", "正在思考...", is_thinking=True)

        # 发起流式请求
        stream = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=self.messages,
            stream=True
        )

        # 初始化累积内容
        current_reasoning = ""
        current_content = ""
        reasoning_printed = False

        # 逐块处理响应
        for chunk in stream:
            delta = chunk.choices[0].delta
            reasoning_delta = getattr(delta, 'reasoning_content', '')
            content_delta = getattr(delta, 'content', '')

            # 处理推理内容
            if reasoning_delta:
                current_reasoning += reasoning_delta
                self.thinking_buffer = current_reasoning
                self.update_thinking_message()

            # 处理回复内容
            if content_delta:
                if reasoning_printed:
                    reasoning_printed = False
                current_content += content_delta
                self.response_buffer = current_content
                self.update_response_message()

        # 将完整回复添加到消息列表
        self.messages.append({"role": "assistant", "content": current_content})

        # 标记请求已完成
        self.is_request_in_progress = False

        # 启用发送按钮和输入框
        self.set_input_state(disabled=False)

    # 显示消息
    def display_message(self, sender, message, is_thinking=False):
        self.chat_history.config(state='normal')
        if is_thinking:
            # 插入思考内容并设置标记
            self.chat_history.insert(tk.END, f"{sender}: {message}\n", "thinking")
            self.thinking_start = self.chat_history.index("end-2c")  # 记录思考内容的起始位置
            self.thinking_end = self.chat_history.index("end-1c")  # 记录思考内容的结束位置
        else:
            self.chat_history.insert(tk.END, f"{sender}: {message}\n")
        self.chat_history.config(state='disabled')
        self.chat_history.yview(tk.END)  # 滚动到底部

    # 更新思考内容
    def update_thinking_message(self):
        self.chat_history.config(state='normal')
        if self.thinking_start and self.thinking_end:
            # 删除旧的思考内容
            self.chat_history.delete(self.thinking_start, self.thinking_end)
        if self.thinking_buffer:
            # 插入新的思考内容
            self.chat_history.insert(self.thinking_start, f"DeepSeek: {self.thinking_buffer}\n", "thinking")
            self.thinking_end = self.chat_history.index("end-1c")  # 更新思考内容的结束位置
        self.chat_history.config(state='disabled')
        self.chat_history.yview(tk.END)

    # 更新回复内容
    def update_response_message(self):
        self.chat_history.config(state='normal')
        if self.response_start and self.response_end:
            # 删除旧的回复内容
            self.chat_history.delete(self.response_start, self.response_end)
        else:
            # 如果是第一次更新回复内容，设置起始位置
            self.response_start = self.chat_history.index("end-1c")
        if self.response_buffer:
            # 插入新的回复内容
            self.chat_history.insert(self.response_start, f"DeepSeek: {self.response_buffer}\n", "response")
            self.response_end = self.chat_history.index("end-1c")  # 更新回复内容的结束位置
        self.chat_history.config(state='disabled')
        self.chat_history.yview(tk.END)

    # 设置输入框和按钮的状态
    def set_input_state(self, disabled):
        if disabled:
            self.user_input.config(state=tk.DISABLED)
            self.send_button.config(state=tk.DISABLED)
        else:
            self.user_input.config(state=tk.NORMAL)
            self.send_button.config(state=tk.NORMAL)

# 运行程序
if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()