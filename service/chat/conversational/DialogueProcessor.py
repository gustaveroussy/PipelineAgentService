# import logging
from loguru import logger
from typing import Union

from langchain_core.messages import HumanMessage
from langchain.prompts import HumanMessagePromptTemplate
from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from service.chat.conversational.ConversationABC import DialogueProcessorABC
from service.chat.conversational.DialoguePipeline import DialoguePipeline
from service.chat.conversational.DialogueMedical import DialogueMedical
# TODO:
# 1. 在对话中接受用户上传的配置文件
# 2. 临时存储用户上传的配置文件
# 3. 多轮对话

# logger = logging.getLogger(__name__)

class DialogueProcessor(DialogueProcessorABC):
    def __init__(self, llm):
        super().__init__(llm=llm)
        self.chat_pipeline = DialoguePipeline(llm=llm)
        self.chat_medical = DialogueMedical()

        self.chat_pipeline_graph = self.chat_pipeline.compile()
        # self.chat_medical_graph = self.chat_medical.compile()
        

    def topic_change(self, state):
        # 如何用户之前没有定义过action，那么就不需要确认
        if state.action not in ["pipeline", "medical"]:
            return False
        
        # 如果用户没有明确改变话题，那么就不需要确认
        if state.messages[-1].content not in ["pipeline", "medical"]:
            return False

        # 如果用户明确改变话题，那么就需要确认
        if state.action != state.messages[-1].content:
            return True
        

    def chat(self, state: BaseModel) -> BaseModel:
        
        def check_invoke(user_msg):
            prompt = self.prompt_data.get("topic_change")
            template = HumanMessagePromptTemplate.from_template(prompt)
            formatted_message = template.format(
                user_message=user_msg,
                previous_action=state.action,
                current_action=state.messages[-1].content
            )
            
            logger.debug(f"formatted_message: {formatted_message}")
            response = self.llm.invoke([formatted_message]) 
            state.messages.append(response)
            return response
        
        def check_interrupt(response):
            answer = interrupt(value=response.content)
            state.messages.append(HumanMessage(content=answer))
            logger.debug(f"answer: {answer}")
            return answer
        
        def check_answer(answer):
            if "yes" in answer.lower().split():
                pass
            elif "no" in answer.lower().split():
                if state.action == "pipeline":
                    state.action = "medical"
                elif state.action == "medical":
                    state.action = "pipeline"
            else:
                check_invoke(answer)


        logger.info(" ---- chat node ---- ")
        response = self.chain.invoke({'user_message':state.messages[-1].content})
        state.messages.append(response)

        if self.topic_change(state):       
            user_msg = next((msg.content for msg in state.messages[::-1] if isinstance(msg, HumanMessage)), None)
            response = check_invoke(user_msg)
            answer = check_interrupt(response)
            check_answer(answer)
        
        if response.content == "pipeline":
            state.action = "pipeline"
        elif response.content == "medical":
            state.action = "medical"

        return state
    
    def pipeline(self, state: BaseModel) -> BaseModel:
        logger.info(" ---- pipeline node ---- ")
        return state
    
    def medical(self, state: BaseModel) -> BaseModel:
        logger.info(" ---- medical node ---- ")
        return state
    
    def route_dialogue(self, state: BaseModel):   
        logger.info(" ---- dialogue router ---- ")
        if state.action == "pipeline":
            return self.pipeline_node
        elif state.action == "medical":
            return self.medical_node
        else:
            return END
    
    def stream_chat_handler(self, chunk) -> str:
        return chunk["chat"]["messages"][-1].content

    def stream_pipeline_handler(self, chunk) -> str:
        # don't show the pipeline messages to stream chat
        return ""

    def stream_medical_handler(self, chunk) -> str:
        # don't show the medical messages to stream chat
        return ""
    
    def stream_nodes_handler(self, chunk: dict) -> str:
        if "chat" in chunk:
            return chunk["chat"]["messages"][-1].content
        
        if "pipeline" in chunk:
            return self.stream_pipeline_handler(chunk)
        
        if "medical" in chunk:
            return self.stream_medical_handler(chunk)
        
        if "messages" in chunk:
            return chunk["messages"][-1].content
        