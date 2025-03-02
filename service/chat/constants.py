from enum import Enum

DO_KEY = "do"
ARGS_KEY = "args"

RQ_JOB_ID_KEY = "rq_job_id"
PROJECT_NAME_KEY = "project_name"
BATCH_ID_KEY = "batch_id"
Sequencing_Type_KEY = "sequencing_type"
Pipeline_Type_KEY = "pipeline_type"
Pipeline_Name_KEY = "pipeline_name"
Sequencing_Species_KEY = "sequencing_species"
Analysis_Mode_KEY = "analysis_mode"
DataSource_Type_KEY = "data_source_type"
WORKING_DIR_KEY = "working_dir"
CREATE_DATE_KEY = "create_date"

KEYWORD_TOPICS_KEY = "keyword_topics"

class PipelineType(Enum):
    """
    工作流的每个阶段都有一个类型，包括command, scripts, nextflow 或者 snakemake
    """
    COMMAND = "command"
    SCRIPTS = "scripts"
    NEXTFLOW = "nextflow"
    SNAKEMAKE = "snakemake"

class PipelineTaskAction(Enum):
    """
    流水线任务是使用某一个特定的流水线分析用户指定的数据的任务，用户可以创建，删除，展示，更新或者展示所有任务
    """
    NEW = "new_pipeline_task"
    DEL = "del_pipeline_task"
    SHOW = "show_pipeline_task"
    UPDATE = "update_pipeline_task"
    SHOW_ALL = "show_all_pipeline_tasks"

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

