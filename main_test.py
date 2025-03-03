import yaml
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser


from service import DialoguePipeline, pipeline_prompt_builder
from service.states import PipelineState

def test_prompt(llm):
    # 实例化一个Ollama对象。
    task_name = "task_new"
    state = PipelineState(messages=[])
    prompts_builder = pipeline_prompt_builder()
    formatter_prompt, question_prompt = prompts_builder.new_pipeline_task_prompt(state, task_name)

    def build_tip(response, task_name, state):
        state, changed = prompts_builder.formatter_update_state(response, state)
        return prompts_builder.build_tip(task_name, state, changed)

    chain = (
        RunnableParallel(
            user_input = RunnablePassthrough(),
            formatter_output = formatter_prompt | llm )
        | RunnableParallel(
            user_input = lambda x: x["user_input"],
            tip = lambda x: build_tip(x["formatter_output"], task_name, state))
        | question_prompt
        | llm        
    )

    msg1 = "I need to process WES data for the project STING_UNLOCK"
    msg2 = "I prefer to use nfcore/Sarek for the analysis"
    msg3 = "I think there are both human and mouse samples."

    state.messages.append(HumanMessage(content=msg1))
    response = chain.invoke({
        "user_input": msg1, 
    })

    # print("response: ", response.content)
    # print("state.args -> ", state.args)
    # print("\n================================\n")

    state.messages.append(HumanMessage(content=msg2))
    response = chain.invoke({
        "user_input": msg2, 
    })

    # print("response: ", response.content)    
    # print("state.args -> ", state.args)
    # print("\n================================\n")
    
    state.messages.append(HumanMessage(content=msg3))
    response = chain.invoke({
        "user_input": msg3, 
    })

    print("response: ", response.content)
    # print("state.args -> ", state.args)    

if __name__ == "__main__":
    llm = ChatOllama(
        temperature = 0.7,
        model = 'qwen2.5:7b',
    )

    test_prompt(llm=llm)
