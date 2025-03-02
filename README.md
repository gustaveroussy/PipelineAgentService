# PipelineAgent

# 重构记录：
1. 完全使用open-webui作为前端，少量修改代码，轻量配置，以省去大量维护前端的工作
2. 后端使用vinference封装vllm，开发环境使用ollama快速搭建大语言模型的服务
3. 使用LangServe将智能体封装成为REST API的微服务，专注于流程管理的部分
4. 使用LangGraph重构工作流，在需要人工确定的重要操作上引入人机交互(human-in-the-loop)
5. 简化LangChain的调用，使其专注于构建思维链CoT
6. Intro ReAct(Reasoning and Action) to 数据处理流水线的值守进程使用
7. 对常见的流水线的问题构建简易的知识库，让值守程序可以自行解决大部分问题
8. 优化提示词
9. 使用生产者-消费者模式管理数据流水线任务
    - 与用户的对话生产任务
    - 任务在RQ(Redis Queue)中管理
    - RQ值守队列，消费队列中的任务
10. 封装工具调用
11. LangSmith对调用的调试和跟踪
12. 认证服务通信
13. 优化相应: invoke() -> stream()

