import os
from enum import Enum
from datetime import datetime 
from typing import Annotated, Optional, TypedDict

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_core.messages import AnyMessage, BaseMessage, ToolMessage, AIMessage
from langchain_core.tools import InjectedToolCallId, tool
from langchain_ollama import ChatOllama

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command, interrupt

from random import randint

# TODO:
# 1. 为每个阶段添加具体的执行逻辑
# 2. 添加工作流程的状态转换逻辑
# 3. 持久化工作流程的状态（Redis， PostgreSQL， MySQL， sqlite）
# 4. 创建轮询服务，定期检查更新工作流程的状态
# 5. 添加工作流程的异常处理逻辑
# 6. 添加工作流程的日志记录
# 7. 封装指令和脚本，比如查询Slurm任务状态，查询文件MD5值等
# 8. 小任务的调度和执行（RQ： redis queue）
# 9. 完善状态的内容，比如添加时间戳，执行结果，执行日志等
# 10. 可扩展，通过配置文件扩展可以支持更多的pipeline

class PipelineType(Enum):
    """
    工作流的每个阶段都有一个类型，包括command, scripts, nextflow 或者 snakemake
    """
    COMMAND = "command"
    SCRIPTS = "scripts"
    NEXTFLOW = "nextflow"
    SNAKEMAKE = "snakemake"

class PipelineStatus(Enum):
    """
    工作流的每个阶段都有一个状态，包括init, running, completed, failed, auto-resume 或者 human-intervention
    """
    INIT    = "init"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    AUTO_RESUME = "auto-resume"
    HUMAN_INTERVENTION = "human-intervention"

class AnalysisWorkflowStages(Enum):
    """
    以下为异步工作流程的九个阶段，每个阶段都被视为一个独立的工作流水线，流水线的类型和状态参见PipelineType和PipelineStatus
    1. INIT: 初始化阶段创建相关工作目录结构，准备执行脚本以及配置文件
    2. DOWNLOADING: 下载数据
    3. MD5CHECKING: MD5校验
    4. DATAPREPARING: 数据准备工作包括数据合并，数据重命名，建立数据指针等
    5. ANALYZING: 数据分析
    6. BACKINGUP: 数据备份
    7. CLEANINGUP: 清理分析中产生的临时文件，移除不常用的大文件
    8. NOTIFY: 通知用户分析结果
    9. COMPLETED: 工作流程完成
    """
    INIT          = "init"
    DOWNLOADING   = "downloading"
    MD5CHECKING   = "md5-checking"
    DATAPREPARING = "data-preparing"
    ANALYZING     = "analyzing"
    BACKINGUP     = "backing-up"
    CLEANINGUP    = "cleaning-up"
    NOTIFY        = "notify"
    COMPLETED     = "completed"

class StageState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    execute: bool = Field(True, description = "Whether the stage is to be executed")
    resume_count: int = Field(0, description = "The number of times the stage has been resumed")

class PipelineState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    # action:   Annotated[str, Field(description="The action to be taken regarding to the tasks of pipeline")]

class PipelineWorkflow(StateGraph):
    def __init__(self, checkpointer = MemorySaver()):
        super().__init__(PipelineState)
        self.checkpointer = checkpointer
        self.stage_dict = {}
        for stage in AnalysisWorkflowStages:
            stage_builder = StateGraph(StageState)
            stage_builder.add_node(PipelineStatus.INIT.value, self.pipeline_init)
            stage_builder.add_node(PipelineStatus.RUNNING.value, self.pipeline_running)
            stage_builder.add_node(PipelineStatus.COMPLETED.value, self.pipeline_completed)
            stage_builder.add_node(PipelineStatus.FAILED.value, self.pipeline_failed)
            stage_builder.add_node(PipelineStatus.AUTO_RESUME.value, self.pipeline_auto_resume)
            stage_builder.add_node(PipelineStatus.HUMAN_INTERVENTION.value, self.pipeline_human_intervention)            
            stage_builder.add_edge(START, PipelineStatus.INIT.value)
            stage_builder.add_edge(PipelineStatus.INIT.value, PipelineStatus.RUNNING.value)
            stage_builder.add_conditional_edges(PipelineStatus.RUNNING.value, 
                                                self.route_state_running, 
                                                [PipelineStatus.COMPLETED.value, 
                                                 PipelineStatus.FAILED.value, 
                                                 PipelineStatus.HUMAN_INTERVENTION.value])
            stage_builder.add_conditional_edges(PipelineStatus.FAILED.value,
                                                self.route_state_failed,
                                                [PipelineStatus.AUTO_RESUME.value,
                                                 PipelineStatus.HUMAN_INTERVENTION.value])
            stage_builder.add_edge(PipelineStatus.AUTO_RESUME.value, PipelineStatus.RUNNING.value)
            stage_builder.add_edge(PipelineStatus.HUMAN_INTERVENTION.value, PipelineStatus.RUNNING.value)
            stage_builder.add_edge(PipelineStatus.COMPLETED.value, END)
            self.stage_dict[stage] = stage_builder.compile(checkpointer = self.checkpointer)

        self.add_node(AnalysisWorkflowStages.INIT.value, self.call_stage_init)
        self.add_node(AnalysisWorkflowStages.DOWNLOADING.value, self.call_stage_download)
        self.add_node(AnalysisWorkflowStages.MD5CHECKING.value, self.call_stage_md5check)
        self.add_node(AnalysisWorkflowStages.DATAPREPARING.value, self.call_stage_dataprepare)
        self.add_node(AnalysisWorkflowStages.ANALYZING.value, self.call_stage_analyze)
        self.add_node(AnalysisWorkflowStages.BACKINGUP.value, self.call_stage_backup)
        self.add_node(AnalysisWorkflowStages.CLEANINGUP.value, self.call_stage_cleanup)
        self.add_node(AnalysisWorkflowStages.NOTIFY.value, self.call_stage_notify)
        self.add_node(AnalysisWorkflowStages.COMPLETED.value, self.call_stage_completed)

        self.add_edge(START, AnalysisWorkflowStages.INIT.value)
        self.add_edge(AnalysisWorkflowStages.INIT.value, AnalysisWorkflowStages.DOWNLOADING.value)
        self.add_edge(AnalysisWorkflowStages.DOWNLOADING.value, AnalysisWorkflowStages.MD5CHECKING.value)
        self.add_edge(AnalysisWorkflowStages.MD5CHECKING.value, AnalysisWorkflowStages.DATAPREPARING.value)
        self.add_edge(AnalysisWorkflowStages.DATAPREPARING.value, AnalysisWorkflowStages.ANALYZING.value)
        self.add_edge(AnalysisWorkflowStages.ANALYZING.value, AnalysisWorkflowStages.BACKINGUP.value)
        self.add_edge(AnalysisWorkflowStages.BACKINGUP.value, AnalysisWorkflowStages.CLEANINGUP.value)
        self.add_edge(AnalysisWorkflowStages.CLEANINGUP.value, AnalysisWorkflowStages.NOTIFY.value)
        self.add_edge(AnalysisWorkflowStages.NOTIFY.value, AnalysisWorkflowStages.COMPLETED.value)
        self.add_edge(AnalysisWorkflowStages.COMPLETED.value, END)
    
    def pipeline_init(self, state: BaseModel) -> BaseModel:
        print("pipeline init")
        state.messages += ["pipeline init"]
        return state

    def pipeline_running(self, state: BaseModel) -> BaseModel:
        print("pipeline running")
        state.messages += ["pipeline running"]
        return state

    def pipeline_completed(self, state: BaseModel) -> BaseModel:
        print("pipeline completed")
        state.messages += ["pipeline completed"]
        return state
    
    def pipeline_failed(self, state: BaseModel) -> BaseModel:
        print("pipeline failed")
        state.messages += ["pipeline failed"]
        return state
    
    def pipeline_auto_resume(self, state: BaseModel) -> BaseModel:
        print("pipeline auto resume")
        state.resume_count += 1
        state.messages += ["pipeline auto resume"]
        return state
    
    def pipeline_human_intervention(self, state: BaseModel) -> BaseModel:
        """
        The pipeline failed. Unfortunately, the agent was unable to automatically resume the pipeline.
        Therefore, it is necessary to contact the bioinformatic team to resume the pipeline manually.
        TODO: send email to bioinformatic team to inform them to check the pipeline and resume it manually
        """
        print("pipeline human intervention")

        # human_response = interrupt({
        #     "question": "The pipeline failed. Unfortunately, the agent was unable to automatically resume the pipeline. Could you contact bioinformatic team to resume the pipeline manually, please? ",
        #     "pipeline_name": pipeline_name,
        # })

        # while not human_response.get("correct", "").lower().startswith("y"):

        state.messages += ["pipeline human intervention"]
        state.resume_count = 0
        return state 
    
    def route_state_running(self, state: BaseModel) -> BaseModel:
        random_number = randint(0, 10)
        if random_number < 4 :
            return PipelineStatus.COMPLETED.value
        else:
            return PipelineStatus.FAILED.value
        
    def route_state_failed(self, state: BaseModel) -> BaseModel:
        if state.resume_count < 2:
            return PipelineStatus.AUTO_RESUME.value
        else:
            return PipelineStatus.HUMAN_INTERVENTION.value
        
    def compile(self):
        return super().compile(checkpointer=self.checkpointer)

    def call_stage_init(self, state: BaseModel) -> BaseModel:
        print("========== call stage init ==========")
        stage_output = self.stage_dict[AnalysisWorkflowStages.INIT].invoke(state)
        return {"messages": stage_output['messages']}
    
    def call_stage_download(self, state: BaseModel) -> BaseModel:
        print("========== call stage download ==========")
        stage_output = self.stage_dict[AnalysisWorkflowStages.DOWNLOADING].invoke(state)
        return {"messages": stage_output['messages']}
    
    def call_stage_md5check(self, state: BaseModel) -> BaseModel:
        print("========== call stage md5 check ==========")
        stage_output = self.stage_dict[AnalysisWorkflowStages.MD5CHECKING].invoke(state)
        return {"messages": stage_output['messages']}
    
    def call_stage_dataprepare(self, state: BaseModel) -> BaseModel:
        print("========== call stage data prepare ==========")
        stage_output = self.stage_dict[AnalysisWorkflowStages.DATAPREPARING].invoke(state)
        return {"messages": stage_output['messages']}
    
    def call_stage_analyze(self, state: BaseModel) -> BaseModel:
        print("========== call stage analyze ==========")
        stage_output = self.stage_dict[AnalysisWorkflowStages.ANALYZING].invoke(state)
        return {"messages": stage_output['messages']}
    
    def call_stage_backup(self, state: BaseModel) -> BaseModel:
        print("========== call stage backup ==========")
        stage_output = self.stage_dict[AnalysisWorkflowStages.BACKINGUP].invoke(state)
        return {"messages": stage_output['messages']}
    
    def call_stage_cleanup(self, state: BaseModel) -> BaseModel:
        print("========== call stage cleanup ==========")
        stage_output = self.stage_dict[AnalysisWorkflowStages.CLEANINGUP].invoke(state)
        return {"messages": stage_output['messages']}
    
    def call_stage_notify(self, state: BaseModel) -> BaseModel:
        print("========== call stage notify ==========")
        stage_output = self.stage_dict[AnalysisWorkflowStages.NOTIFY].invoke(state)
        return {"messages": stage_output['messages']}
    
    def call_stage_completed(self, state: BaseModel) -> BaseModel:
        print("========== call stage completed ==========")
        stage_output = self.stage_dict[AnalysisWorkflowStages.COMPLETED].invoke(state)
        return {"messages": stage_output['messages']}



# # https://langchain-ai.github.io/langgraph/concepts/functional_api/
# from langgraph.func import task

# @task()
# def slow_computation(input_value):
#     # Simulate a long-running operation
#     ...
#     return None

# # Save the image to a file
# image_data = builder.stage_dict[AnalysisWorkflowStages.INIT].get_graph().draw_mermaid_png()
# with open("pipeline_graph.png", "wb") as f:
#     f.write(image_data)

# print("Graph saved as pipeline_graph.png")

############################################################################################# 

# config = {"configurable": {"thread_id": "1"}}

# builder = PipelineWorkflow()
# graph   = builder.compile()
# # response= graph.invoke({"messages": ["start"]}, config, stream_mode="values")
# response= graph.invoke({"messages": ["start"]}, config)

# print(response)
