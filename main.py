import yaml, uuid, time, json
# import logging
from loguru import logger

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from langserve import add_routes
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableLambda
from langchain.prompts import ChatPromptTemplate
from langgraph.errors import GraphInterrupt

from langgraph.types import interrupt, Command

from service import DialogueProcessor

# 配置日志
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# API_KEY = "sk-1f49596c4663696c3fdcbde90481a152"
# API_NAME= "pipeline-agent-api"

# api_key_header = APIKeyHeader(name=API_NAME, auto_error=False)

# # 验证API密钥的依赖函数
# async def verify_api_key(api_key: str = Depends(api_key_header)):
#     if api_key != API_KEY:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid API Key",
#         )
#     return api_key

# 创建应用
app = FastAPI()

# 存储中断的会话
interrupted_threads = {}

with open("config/model.yaml", "r") as f:
    config = yaml.safe_load(f)


llm = ChatOllama(
    model       = config.get("ollama").get("model_name"),
    temperature = config.get("ollama").get("temperature"),
)

chat = DialogueProcessor(llm)
graph = chat.compile()
chat.graph = graph

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应更具体
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加模型列表端点
@app.api_route("/v1/models", methods=["GET", "OPTIONS"])
async def list_models(response: Response):

    # 设置 CORS 头部
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    
    return {
        "object": "list",
        "data": [
            {
                "id": "pipeline-agent",
                "object": "model",
                "created": 1677610602,
                "owned_by": "jinxin.WANG@IGR"
            }
        ]
    }

def build_response(result):
    # 构造响应，包括会话ID以便客户端在后续请求中使用
    response = {
        "id": f"chatcmpl-{hash(str(result)) % 10000}",
        "object": "chat.completion",
        "created": int(__import__("time").time()),
        "model": "pipeline-agent",
        "thread_id": result.get("thread_id"),  # 返回会话ID
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": str(result.get("messages", [])[-1].content 
                                if result.get("messages") else "Sorry, the model has no response.")
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }
    return response

def build_stream_response(input_text, thread_id, delta, finish_reason = None):
    return "data: " + json.dumps({
        "id": f"chatcmpl-{hash(input_text) % 10000}",
        "object": "chat.completion.chunk",
        "created": int(__import__("time").time()),
        "model": "pipeline-agent",
        "thread_id": thread_id,
        "choices": [{
            "index": 0,
            "delta": delta,
            "finish_reason": finish_reason
        }]
    }) + "\n\n"

def openai_response_format_chain(llm, func):
    return llm | RunnableLambda(lambda x: func(x))

chain = openai_response_format_chain(chat.graph, build_response)

add_routes(
    app,
    chain,
    path="/v1/chat",
)

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    input_text = messages[-1].get("content", "") if messages else ""
    interrupt_id = None

    # 安全获取 thread_id
    metadata = data.get("metadata", {})
    thread_id = metadata.get("chat_id") if isinstance(metadata, dict) else str(uuid.uuid4())
    
    config = {
        "configurable": {
            "thread_id": thread_id,
        },
    }

    # 非流式处理方式
    if not data.get("stream", False):
        try:
            result = chat.graph.invoke(
                {'messages': HumanMessage(content=input_text)},
                config=config
            )
            return build_response(result)
        except Exception as e:
            logger.error(f"处理请求时出错: {str(e)}")
            return {"error": str(e)}
    
    def get_interrupt_content(chunk):    
        interrupts = chunk["__interrupt__"]
        
        # 通常只处理第一个中断
        if isinstance(interrupts, tuple) and interrupts:
            return interrupts[0].value, interrupts[0].ns[0]
            
        # 防御性编程 - 如果直接是对象而不是元组
        elif hasattr(interrupts, "value"):
            return interrupts.value, interrupts.ns[0]
            
        return None, None

    def get_content(chunk):      
        if isinstance(chunk, dict) and "__interrupt__" in chunk.keys():
            return chunk["__interrupt__"][0].value
        
        if isinstance(chunk, list) and chunk:
            return chunk[-1].content if hasattr(chunk[-1], "content") else str(chunk[-1])
        
        return str(chunk)

    # 流式处理方式
    def generate_stream():
        try:
            if thread_id in interrupted_threads: 
                interrupt_id = interrupted_threads[thread_id] 
                config["configurable"]["interrupt"] = interrupt_id 
                config["configurable"]["interrupt_response"] = True 
                messages = Command(resume = input_text)
                del interrupted_threads[thread_id]
                logger.info(f"thread_id: {thread_id}, interrupt: {interrupt_id}")
            else:
                messages = {'messages': HumanMessage(content=input_text)}

            stream = chat.graph.stream(
                messages,
                config=config,
            )
            
            # 发送初始响应
            yield build_stream_response(input_text, thread_id, {"role": "assistant"})
            
            # 流式输出响应块
            for chunk in stream:
                # 提取内容
                if isinstance(chunk, dict):
                    if "__interrupt__" in chunk:
                        # 处理中断
                        content, interrupt_id = get_interrupt_content(chunk)
                        interrupted_threads[thread_id] = interrupt_id
                        logger.info(f"thread_id: {thread_id}, interrupt: {interrupt_id}")
                    else:
                        content = chat.stream_nodes_handler(chunk)
                
                if content is None:
                    content = get_content(chunk)

                # 发送文本块
                yield build_stream_response(input_text, thread_id, {"content": content})
            
            # 发送结束标记
            yield build_stream_response(input_text, thread_id, {}, {"finish_reason": "stop"})           
            yield "data: [DONE]\n\n"
        
        except Exception as e:
            logger.error(f"Stream handling error: {str(e)}")
            yield build_stream_response(input_text, thread_id, {"content": f"pipeline-agent service failed to response."}, {"finish_reason": "error"})
            yield "data: [DONE]\n\n"
            raise e

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18888)
