from langgraph.graph import StateGraph, START, END

from service.chat.states import PipelineState

class DialogueMedical(StateGraph):
    """
    对有关复杂医学问题的对话处理器
        1. 防止模型幻觉 RAG
        2. 用通用大模型和推理大模型的交互提升对话质量 CoT+MoE
        3. TODO: 对于病人的数据分析结果进行讨论
    """
    def __init__(self):
        super().__init__(PipelineState)