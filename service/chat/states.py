from typing import Annotated, Optional, TypedDict

from pydantic import BaseModel, Field
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from service.chat.constants import (PipelineTaskAction, AnalysisWorkflowStages, 
                                            DO_KEY, ARGS_KEY, PROJECT_NAME_KEY, CREATE_DATE_KEY, BATCH_ID_KEY,
                                            Sequencing_Type_KEY, Pipeline_Type_KEY, Pipeline_Name_KEY, 
                                            Sequencing_Species_KEY, Analysis_Mode_KEY, DataSource_Type_KEY, 
                                            WORKING_DIR_KEY, RQ_JOB_ID_KEY, KEYWORD_TOPICS_KEY)

class ProcessorState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    action: Optional[str] = Field(None, description = "The action to be taken regarding to the tasks of the pipeline")
    # response: Optional[str] = Field(None, description="The response to the user's input")
    interrupted: Optional[bool] = Field(False, description="Whether the conversation has been interrupted")

class PipelineStateArgsDict(TypedDict):
    DO_KEY: Optional[bool]
    ARGS_KEY: Optional[dict]

class StageState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    execute: bool = Field(True, description = "Whether the stage is to be executed")
    resume_count: int = Field(0, description = "The number of times the stage has been resumed")

init_state_args: PipelineStateArgsDict = {
    DO_KEY: None,
    ARGS_KEY: None
}

download_state_args: PipelineStateArgsDict = {
    DO_KEY: None,
    ARGS_KEY: None
}

md5check_state_args: PipelineStateArgsDict = {
    DO_KEY: None,
    ARGS_KEY: None
}

dataprepare_state_args: PipelineStateArgsDict = {
    DO_KEY: None,
    ARGS_KEY: None
}   

analyze_state_args: PipelineStateArgsDict = {
    DO_KEY: None,
    ARGS_KEY: None
}

backup_state_args: PipelineStateArgsDict = {
    DO_KEY: None,
    ARGS_KEY: None
}   

cleanup_state_args: PipelineStateArgsDict = {
    DO_KEY: None,
    ARGS_KEY: None
}

notify_state_args: PipelineStateArgsDict = {
    DO_KEY: None,
    ARGS_KEY: None
}

completed_state_args: PipelineStateArgsDict = {
    DO_KEY: None,
    ARGS_KEY: None
}

class PipelineState(BaseModel):
    messages: Annotated[list[AnyMessage], add_messages]
    action: Optional[PipelineTaskAction] = Field(None, description = "The action to be taken regarding to the tasks of the pipeline")
    # tool_call_id: Optional[str] = Field(..., description="The unique ID for the tool call")

    username: Optional[str] = Field(None, description="The username of the user who initiated the pipeline task")
    email: Optional[str]    = Field(None, description="The email of the user who initiated the pipeline task")
    args: Optional[dict]    = Field({
        RQ_JOB_ID_KEY: None,
        PROJECT_NAME_KEY: None,
        CREATE_DATE_KEY: None,
        BATCH_ID_KEY: None,
        WORKING_DIR_KEY: None,
        Sequencing_Type_KEY: None,
        Pipeline_Type_KEY: None,
        Pipeline_Name_KEY: None,
        Sequencing_Species_KEY: None,
        Analysis_Mode_KEY: None,
        DataSource_Type_KEY: None, 
        KEYWORD_TOPICS_KEY: None,
        AnalysisWorkflowStages.INIT: init_state_args,
        AnalysisWorkflowStages.DOWNLOADING: download_state_args,
        AnalysisWorkflowStages.MD5CHECKING: md5check_state_args,
        AnalysisWorkflowStages.DATAPREPARING: dataprepare_state_args,
        AnalysisWorkflowStages.ANALYZING: analyze_state_args,
        AnalysisWorkflowStages.BACKINGUP: backup_state_args,
        AnalysisWorkflowStages.CLEANINGUP: cleanup_state_args,
        AnalysisWorkflowStages.NOTIFY: notify_state_args,
        AnalysisWorkflowStages.COMPLETED: completed_state_args
    }, description="The arguments for the pipeline task")

