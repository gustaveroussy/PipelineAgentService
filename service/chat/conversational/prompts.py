import yaml
from typing import Literal
from langchain.prompts import (PromptTemplate, 
                               ChatPromptTemplate, 
                               HumanMessagePromptTemplate, 
                               AIMessagePromptTemplate, 
                               SystemMessagePromptTemplate, 
                               FewShotPromptTemplate, 
                               FewShotChatMessagePromptTemplate)
from pydantic import BaseModel


from service.chat.states import PipelineState
from service.chat.constants import (PipelineTaskAction,
                                            PROJECT_NAME_KEY, BATCH_ID_KEY, 
                                            Sequencing_Type_KEY, Pipeline_Type_KEY,
                                            Pipeline_Name_KEY, Sequencing_Species_KEY,
                                            Analysis_Mode_KEY, DataSource_Type_KEY, KEYWORD_TOPICS_KEY)

constants_dict = {"ProjectNameKey": PROJECT_NAME_KEY,
                  "BatchIDKey": BATCH_ID_KEY,
                  "SequencingTypeKey": Sequencing_Type_KEY,
                  "PipelineTypeKey": Pipeline_Type_KEY,
                  "PipelineNameKey": Pipeline_Name_KEY,
                  "SequencingSpeciesKey": Sequencing_Species_KEY,
                  "AnalysisModeKey": Analysis_Mode_KEY,
                  "DataSourceTypeKey": DataSource_Type_KEY}

class pipeline_prompt_builder:
    def __init__(self, prompt_file="config/prompts/pipeline/pipeline_task_new.yaml"):
        self.prompt_file = prompt_file
        with open(prompt_file, "r") as f : 
            self.prompt_data = yaml.safe_load(f)

    def load_system_prompts(self, task_name, constants_dict = constants_dict):
        system_template = self.prompt_data.get(task_name).get("system").format(**constants_dict)
        system_prompt = SystemMessagePromptTemplate.from_template(system_template)
        return system_prompt
    
    def load_output_prompts(self, task_name, prompt_type: str = Literal["formatter", "question", None]):
        output_template = self.prompt_data.get(task_name).get("output").get(prompt_type)
        output_prompt = SystemMessagePromptTemplate.from_template(output_template)
        return output_prompt
    
    def load_msg_format_prompts(self, task_name, prompt_type: str = Literal["formatter", "question", None], constants_dict = constants_dict):
        message_template = self.prompt_data.get(task_name).get("message").get(prompt_type).format(**constants_dict)
        # message_prompt = SystemMessagePromptTemplate.from_template(message_template)
        message_prompt = HumanMessagePromptTemplate.from_template(message_template)
        return message_prompt

    def load_few_shot_prompts(self, task_name, prompt_type: str = Literal["formatter", "question", None], few_shot_type: str = Literal["single-turn", "multi-turn"], constants_dict = constants_dict):

        examples = [[{'user':      item.get(prompt_type).get('user').format(**constants_dict),
                      'assistant': item.get(prompt_type).get('assistant').format(**constants_dict)}
                        for item in examples if item.get(prompt_type) is not None ]
                            for examples in self.prompt_data.get(task_name).get(few_shot_type) ]
        
        prompts = [ FewShotChatMessagePromptTemplate(
            # example_prompt = ChatPromptTemplate.from_messages([("human", "{user}"), ("ai", "{assistant}")]),
            example_prompt = (
                HumanMessagePromptTemplate.from_template("{user}") + AIMessagePromptTemplate.from_template("{assistant}")
            ),
            examples = example, 
        ) for example in examples ]

        # print("====================================")
        # print("prompts: ", prompts)
        # print("====================================")

        return prompts

    def load_prompts(self, task_name, prompt_type: str = Literal["formatter", "question", None], constants_dict = constants_dict):
        system_prompt = self.load_system_prompts(task_name, constants_dict)
        output_prompt = self.load_output_prompts(task_name, prompt_type)
        ai_msg_format_prompt = self.load_msg_format_prompts(task_name, prompt_type,   constants_dict)
        single_turn_prompts  = self.load_few_shot_prompts(task_name, prompt_type, "single-turn", constants_dict)
        multi_turn_prompts   = self.load_few_shot_prompts(task_name, prompt_type, "multi-turn",  constants_dict)
        # end_prompt = self.load_end_prompts(task_name)

        # 定义主要提示模板，包含系统提示、few-shot示例和人类信息提示
        prompt = ChatPromptTemplate.from_messages(
            [system_prompt,
             output_prompt,
             *single_turn_prompts,
             *multi_turn_prompts,
             ai_msg_format_prompt])

        return prompt

    def get_missing_key(self, state: PipelineState) -> str:
        if state.args.get(PROJECT_NAME_KEY) is None:
            return PROJECT_NAME_KEY
        if state.args.get(Sequencing_Type_KEY) is None:
            return Sequencing_Type_KEY
        # if state.args.get(Pipeline_Type_KEY) is None:
        #     return Pipeline_Type_KEY
        if state.args.get(Pipeline_Name_KEY) is None:
            return Pipeline_Name_KEY
        if state.args.get(Sequencing_Species_KEY) is None:
            return Sequencing_Species_KEY
        if state.args.get(Analysis_Mode_KEY) is None:
            return Analysis_Mode_KEY
        if state.args.get(DataSource_Type_KEY) is None:
            return DataSource_Type_KEY
        if state.args.get(BATCH_ID_KEY) is None:
            return BATCH_ID_KEY

    def new_pipeline_task_prompt(self, state: PipelineState, task_name = "task_new"):
        d = constants_dict.copy()
        d["ProjectNameValue"] = state.args.get(PROJECT_NAME_KEY)
        d["BatchIDValue"] = state.args.get(BATCH_ID_KEY)
        d["SequencingTypeValue"] = state.args.get(Sequencing_Type_KEY)
        d["PipelineTypeValue"] = state.args.get(Pipeline_Type_KEY)
        d["PipelineNameValue"] = state.args.get(Pipeline_Name_KEY)
        d["SequencingSpeciesValue"] = state.args.get(Sequencing_Species_KEY)
        d["AnalysisModeValue"] = state.args.get(Analysis_Mode_KEY)
        d["DataSourceTypeValue"] = state.args.get(DataSource_Type_KEY)
        # d["missing_key"] = self.get_missing_key(state)
        formatter_prompt= self.load_prompts(task_name = task_name, prompt_type = "formatter", constants_dict = d)
        question_prompt = self.load_prompts(task_name = task_name, prompt_type = "question",  constants_dict = d)
        return formatter_prompt, question_prompt

    def del_pipeline_task_prompt(self, state: PipelineState):
        return

    def update_pipeline_task_prompt(self, state: PipelineState):
        return

    def show_pipeline_task_prompt(self, state: PipelineState):
        return  

    def show_all_pipeline_tasks_prompt(self, state: PipelineState):
        return

    def default_pipeline_prompt(self, state: PipelineState):
        return

    def pipeline_chat_prompt(self, state: PipelineState):
        if state.action == PipelineTaskAction.NEW:
            return self.new_pipeline_task_prompt(state)
        elif state.action == PipelineTaskAction.DEL:
            return self.del_pipeline_task_prompt(state)
        elif state.action == PipelineTaskAction.UPDATE:
            return self.update_pipeline_task_prompt(state)
        elif state.action == PipelineTaskAction.SHOW:
            return self.show_pipeline_task_prompt(state)
        elif state.action == PipelineTaskAction.SHOW_ALL:
            return self.show_all_pipeline_tasks_prompt(state)
        else:
            return self.default_pipeline_prompt(state)
        

    def formatter_update_state(self, response, state):

        print("response: ", response.content)

        changed = False
        special_chars = '@#$%"\',.!?[]{}()=+-*/&^%~`'
        translator = str.maketrans('', '', special_chars)
        yaml_data = "\n".join([line.lstrip().translate(translator) for line in response.content.splitlines() if ":" in line])
        for k,v in yaml.safe_load(yaml_data).items():
            if v is None or v.strip() == "None" or v.strip() == "":
                continue
            if k == Sequencing_Species_KEY and v.strip().lower() not in ('human', 'mouse'):
                continue
            if state.args.get(k) is None:
                state.args.update({k: v})
                changed = True
        return state, changed
    
    def build_tip(self, task_name, state: BaseModel, changed):

        if None not in state.args.values():
            return None
        
        if changed:
            missing_key = self.get_missing_key(state)
            print("missing_key: ", missing_key)
            state.args.update({KEYWORD_TOPICS_KEY: missing_key})
            return self.prompt_data.get(task_name).get('tip').get('success').format({"missing_key": missing_key})
        
        else:
            return self.prompt_data.get(task_name).get('tip').get('fail').format({"topic_key": state.args.get(KEYWORD_TOPICS_KEY)})
        
        