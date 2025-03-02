import os
import yaml
from abc import ABC, abstractmethod


class ChatBotABC(ABC):
    @abstractmethod
    def _init_llm(self):
        pass

    @abstractmethod
    def _init_memory(self):
        pass

    @abstractmethod
    def _init_chatbot(self):
        pass

