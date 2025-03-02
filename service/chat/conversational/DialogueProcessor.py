# import logging
from loguru import logger
from typing import Union

from langchain_core.messages import HumanMessage
from langchain.prompts import HumanMessagePromptTemplate
from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from service.chat.conversational.ConversationABC import DialogueProcessorABC

# TODO:
# 1. 在对话中接受用户上传的配置文件
# 2. 临时存储用户上传的配置文件
# 3. 多轮对话

# logger = logging.getLogger(__name__)

class DialogueProcessor(DialogueProcessorABC):

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

        logger.info(" ---- chat node ---- ")
        response = self.chain.invoke({'user_message':state.messages[-1].content})
        state.messages.append(response)

        if self.topic_change(state): 
            prompt = self.prompt_data.get("topic_change")
            user_msg = next((msg.content for msg in state.messages[::-1] if isinstance(msg, HumanMessage)), None)

            template = HumanMessagePromptTemplate.from_template(prompt)
            formatted_message = template.format(
                user_message=user_msg,
                previous_action=state.action,
                current_action=state.messages[-1].content
            )
            
            logger.info(f"formatted_message: {formatted_message}")
            response = self.llm.invoke([formatted_message]) 
            state.messages.append(response)

            answer = interrupt(value=response.content)
            state.messages.append(HumanMessage(content=answer))
            logger.info(f"answer: {answer}")
            
            if "yes" not in answer.lower().split():
                # tmp 
                if state.action == "pipeline":
                    state.action = "medical"
                elif state.action == "medical":
                    state.action = "pipeline"
                state.messages.append(HumanMessage(content=state.action))
                
        elif response.content == "pipeline":
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
        return ""

    def stream_medical_handler(self, chunk) -> str:
        return ""
    
    def stream_nodes_handler(self, chunk: dict) -> str:
        if "chat" in chunk:
            return chunk["chat"]["messages"][-1].content
        
        if "pipeline" in chunk:
            return ""
        
        if "medical" in chunk:
            return ""
        
        if "messages" in chunk:
            return chunk["messages"][-1].content
        