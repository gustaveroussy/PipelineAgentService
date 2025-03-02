import yaml
from abc import ABC, abstractmethod

from langgraph.checkpoint.memory import MemorySaver
from service.chat.states import ProcessorState, PipelineState
from langgraph.graph import StateGraph, START, END
from langchain.prompts import (SystemMessagePromptTemplate,
                               FewShotPromptTemplate,
                               FewShotChatMessagePromptTemplate,
                               HumanMessagePromptTemplate,
                               PromptTemplate,
                               ChatPromptTemplate)
# TODO:
# 1. 在对话中接受用户上传的配置文件
# 2. 临时存储用户上传的配置文件
# 3. 多轮对话


class DialogueProcessorABC(StateGraph, ABC):

    chat_node = "chat"
    pipeline_node = "pipeline"
    medical_node = "medical"

    def __init__(self, llm, checkpoint = MemorySaver(), prompt_file = "config/prompts/DialogueProcessor.yaml"):
        super().__init__(ProcessorState)
        self.checkpointer = checkpoint
        self.prompt_file = prompt_file
        with open(prompt_file, "r") as f:
            self.prompt_data = yaml.safe_load(f)

        self.prompts = self.load_prompts()
        self.llm = llm
        self.chain = self.prompts | self.llm
        self.add_node(self.chat_node, self.chat)
        self.add_node(self.pipeline_node, self.pipeline)
        self.add_node(self.medical_node, self.medical)
        
        self.set_entry_point(self.chat_node)
        self.add_conditional_edges(self.chat_node, 
                                   self.route_dialogue, 
                                   [self.medical_node, 
                                    self.pipeline_node, 
                                    END])
        self.set_finish_point(self.medical_node)
        self.set_finish_point(self.pipeline_node)

    def load_system_prompts(self):
        system_prompt = SystemMessagePromptTemplate.from_template(self.prompt_data.get("system"))
        return system_prompt
    
    def load_few_shot_prompts(self):

        examples = [{'user':      item.get('user'), 
                     'assistant': item.get('assistant')} 
                        for item in self.prompt_data.get("examples")]
        
        template = PromptTemplate(
            input_variables = ["user", "assistant"],
            template = "user: {user}\nassistant: {assistant}"
        )

        prompts = FewShotPromptTemplate(
            example_prompt = template,
            examples = examples,
            prefix = "the following is a single-turn conversation example: ",
            suffix = "----"
        )

        few_shot_message = HumanMessagePromptTemplate(prompt = prompts)
    
        return few_shot_message
    

    def load_message_prompts(self):
        message_prompt = ChatPromptTemplate.from_template(self.prompt_data.get("message"))
        return message_prompt
    
    def load_prompts(self):
        system_prompt = self.load_system_prompts()
        few_shot_prompts = self.load_few_shot_prompts()
        message_prompt = self.load_message_prompts()
        prompt = ChatPromptTemplate.from_messages([
            system_prompt, 
            few_shot_prompts, 
            message_prompt
        ])

        print(prompt)

        return prompt

    def compile(self, checkpointer = None, *, store = None, interrupt_before = None, interrupt_after = None, debug = False, name = None):
        if checkpointer is None:
            checkpointer = self.checkpointer
        return super().compile(checkpointer = checkpointer, store=store, interrupt_before=interrupt_before, interrupt_after=interrupt_after, debug=debug, name=name)

    @abstractmethod
    def chat(self, state):
        pass

    @abstractmethod
    def pipeline(self, state):
        pass

    @abstractmethod
    def medical(self, state):
        pass

    @abstractmethod
    def route_dialogue(self, state):
        pass

class DialoguePipelineABC(StateGraph, ABC):
    """
    有关数据处理流水线任务管理的对话处理器，该对话处理器用于管理数据处理流水线任务的增删改查
        update_chat_state: 调用本地小模型解析对话内容，并更新对话状态
        new_pipeline:      创建新的数据处理流水线任务
        del_pipeline:      删除数据处理流水线任务
        change_pipeline:   修改数据处理流水线任务
        show_pipeline:     查看数据处理流水线任务的具体信息
        show_all:          查看所有数据处理流水线任务列表
    """
    def __init__(self):
        super().__init__(PipelineState)
        self.add_node("update_chat_state", self.update_chat_state)
        self.add_node("new_pipeline",    self.pipeline_new_task)
        self.add_node("del_pipeline",    self.pipeline_del_task)
        self.add_node("change_pipeline", self.pipeline_change_task)
        self.add_node("show_pipeline",   self.pipeline_show_task)
        self.add_node("show_all",        self.pipeline_show_all)

        self.add_edge(START, "update_chat_state")
        self.add_conditional_edges("update_chat_state", 
                                   self.route_chat, 
                                   ["new_pipeline", "del_pipeline", 
                                    "change_pipeline", "show_pipeline", 
                                    "show_all", END])
        
        self.add_edge("new_pipeline", END)
        self.add_edge("del_pipeline", END)
        self.add_edge("change_pipeline", END)
        self.add_edge("show_pipeline", END)

    @abstractmethod
    def update_chat_state(self, state):
        pass

    @abstractmethod
    def pipeline_new_task(self, state):
        pass

    @abstractmethod
    def pipeline_del_task(self, state):
        pass

    @abstractmethod
    def pipeline_change_task(self, state):
        pass

    @abstractmethod
    def pipeline_show_task(self, state):
        pass

    @abstractmethod
    def pipeline_show_all(self, state):
        pass

    @abstractmethod
    def route_chat(self, state):
        pass


class DialogueMedical(StateGraph):
    """
    对有关复杂医学问题的对话处理器
        1. 防止模型幻觉 RAG
        2. 用通用大模型和推理大模型的交互提升对话质量 CoT+MoE
        3. TODO: 对于病人的数据分析结果进行讨论
    """
    def __init__(self):
        super().__init__(PipelineState)
