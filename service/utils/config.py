import yaml
from langchain_ollama import ChatOllama

def load_model(config = "config/model.yaml"):
    
    with open(config, "r") as f:
        config = yaml.safe_load(f)

    llm = ChatOllama(
        model       = config.get("ollama").get("model_name"),
        temperature = config.get("ollama").get("temperature"),
    )

    return llm