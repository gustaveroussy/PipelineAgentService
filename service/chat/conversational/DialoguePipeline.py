from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_ollama import ChatOllama

from langchain_core.tools import InjectedToolCallId, tool
from langchain_core.messages import AnyMessage, BaseMessage, ToolMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate

from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel

from service.chat.states import PipelineState
from service.chat.constants import PipelineTaskAction
from service.chat.pipeline.prompts import pipeline_prompt_builder

from service.utils.config import load_model

class DialoguePipeline(StateGraph):
    """
    有关数据处理流水线任务管理的对话处理器，该对话处理器用于管理数据处理流水线任务的增删改查
        update_chat_state:    调用本地小模型解析对话内容，并更新对话状态
        pipeline_new_task:    创建新的数据处理流水线任务
        del_pipeline_task:    删除数据处理流水线任务
        pipeline_update_task: 修改数据处理流水线任务
        pipeline_show_task:   查看数据处理流水线任务的具体信息
        pipeline_show_all:    查看所有数据处理流水线任务列表
        route_chat:           根据对话内容路由到不同的任务

    TODO: double consider if it needs to decorate these methods with @tool
    """
    def __init__(self, checkpointer = None, llm = None):
        super().__init__(PipelineState)

        if llm is None: 
            llm = load_model()

        if checkpointer is None:
            checkpointer = MemorySaver()
        
        self.llm = llm
        self.checkpointer = checkpointer

        self.add_node("chat_with_state", self.chat_with_state)
        self.add_node("update_chat_state", self.update_chat_state)
        self.add_node(PipelineTaskAction.NEW.value,    self.pipeline_new_task)
        self.add_node(PipelineTaskAction.DEL.value,    self.pipeline_del_task)
        self.add_node(PipelineTaskAction.UPDATE.value, self.pipeline_update_task)
        self.add_node(PipelineTaskAction.SHOW.value,   self.pipeline_show_task)
        self.add_node(PipelineTaskAction.SHOW_ALL.value, self.pipeline_show_all)

        self.add_edge(START, "chat_with_state")
        self.add_edge("chat_with_state", "update_chat_state")
        self.add_conditional_edges("update_chat_state", 
                                   self.route_chat, 
                                   [PipelineTaskAction.NEW.value,
                                    PipelineTaskAction.DEL.value,
                                    PipelineTaskAction.UPDATE.value,
                                    PipelineTaskAction.SHOW.value,
                                    PipelineTaskAction.SHOW_ALL.value,
                                    END])
        
        self.add_edge(PipelineTaskAction.NEW.value, END)
        self.add_edge(PipelineTaskAction.DEL.value, END)
        self.add_edge(PipelineTaskAction.UPDATE.value, END)
        self.add_edge(PipelineTaskAction.SHOW.value, END)
        self.add_edge(PipelineTaskAction.SHOW_ALL.value, END)

    def chat_with_state(self, state: PipelineState) -> PipelineState:
        """
        与用户进行对话，并将对话状态传递给下一个节点
        """
        print("与用户进行对话")
        # prompt = pipeline_prompt_builder(state)
        # response = self.llm.invoke(prompt)
        # state.messages.append(SystemMessage(content = response))
        return state

    def update_chat_state(self, state: PipelineState) -> PipelineState:
        """
        调用本地小模型解析对话内容，并更新对话状态
        """
        print("更新对话状态")

        # Instantiation using from_template (recommended)
        prompt = PromptTemplate.from_template("You are an powerful content extractor, {foo}")
        # prompt.format(foo="bar")

        # Instantiation using initializer
        # prompt = PromptTemplate(template="Say {foo}")

        for msg in reversed(state.messages):
            if isinstance(msg, HumanMessage):
                # print(msg)
                chain = prompt | self.llm
                print(msg.content)
                response = chain.invoke([{"foo": msg.content}])
                # print the content of the response message from the local language model
                # print(response.content)
                print(response)
                break

        if state.args is None:
            state.messages.append(AIMessage(content=msg.content))

        return state
    
    def pipeline_new_task(self, state: PipelineState) -> PipelineState:
        """
        创建新的数据处理流水线任务
        """
        print("创建新的数据处理流水线任务")
        return state
    
    def pipeline_del_task(self, state: PipelineState) -> PipelineState:
        """
        删除数据处理流水线任务
        """
        print("删除数据处理流水线任务")
        return state
    
    def pipeline_update_task(self, state: PipelineState) -> PipelineState:  
        """
        修改数据处理流水线任务
        """
        print("修改数据处理流水线任务")
        return state
    
    def pipeline_show_task(self, state: PipelineState) -> PipelineState:
        """
        查看数据处理流水线任务的具体信息
        """
        print("查看数据处理流水线任务的具体信息")
        return state    
    
    def pipeline_show_all(self, state: PipelineState) -> PipelineState:
        """
        查看所有数据处理流水线任务列表
        """
        print("查看所有数据处理流水线任务列表")
        return state
    
    def route_chat(self, state: PipelineState) -> str:
        """
        根据对话内容路由到不同的任务
        """
        print("路由对话")
        if state.action == PipelineTaskAction.NEW:
            return PipelineTaskAction.NEW.value
        elif state.action == PipelineTaskAction.DEL:
            return PipelineTaskAction.DEL.value
        elif state.action == PipelineTaskAction.UPDATE:
            return PipelineTaskAction.UPDATE.value
        elif state.action == PipelineTaskAction.SHOW:
            return PipelineTaskAction.SHOW.value
        elif state.action == PipelineTaskAction.SHOW_ALL:
            return PipelineTaskAction.SHOW_ALL.value
        else:
            return "__end__"
    
    def compile(self):
        """
        编译对话处理器
        """
        self.graph = super().compile(checkpointer=self.checkpointer)
        return self.graph

    

