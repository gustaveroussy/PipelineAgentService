PipelineAgentService is a microservice designed to empower biologists and doctors, even those without command-line interface (CLI) expertise, to effortlessly launch data analysis pipelines on the Flamingo platform. This AI agent is engineered for self-sufficiency, autonomously monitoring and maintaining pipeline operations.  It possesses the capability to resolve common failure scenarios and automatically recover pipeline execution, ensuring smooth and continuous data processing. In situations where the Agent encounters issues beyond its automated resolution capabilities, it will proactively engage engineers to seek solutions, minimizing downtime and ensuring reliable pipeline performance.

## Service Architecture Diagram
![Service Architecture](https://github.com/gustaveroussy/PipelineAgentService/blob/main/img/PipelineAgentServiceArch.jpg)

## Refactoring Records:

1.  **Frontend Overhaul:** Fully adopted open-webui as the frontend, implementing minor code modifications and lightweight configurations to significantly reduce frontend maintenance efforts.
2.  **Backend Enhancement:** Utilized vinference to encapsulate vllm for the backend, and employed ollama in the development environment for rapid deployment of large language model services.
3.  **Microservice Architecture:** Encapsulated the agent as a REST API microservice using LangServe, concentrating on process management functionalities.
4.  **Workflow Re-engineering with Human-in-the-Loop:**  Rebuilt the workflow using LangGraph, incorporating human-in-the-loop interaction for crucial operations requiring manual verification.
5.  **LangChain Simplification:** Streamlined LangChain invocations, directing its focus towards constructing Chain-of-Thought (CoT) reasoning.
6.  **Integration of ReAct for Watchdog Process:** Introduced ReAct (Reasoning and Action) framework to enhance the watchdog process of the data processing pipeline.
7.  **Knowledge Base for Self-Resolution:** Developed a basic knowledge base addressing common pipeline issues, empowering the watchdog program to autonomously resolve the majority of problems.
8.  **Prompt Optimization:** Refined and improved prompt design.
9.  **Producer-Consumer Task Management:** Implemented a producer-consumer pattern to manage data pipeline tasks:
    *   User conversations generate tasks (task production).
    *   Tasks are managed within RQ (Redis Queue).
    *   RQ monitors and processes tasks from the queue (task consumption).
10. **Tool Call Encapsulation:**  Wrapped and abstracted tool invocations.
11. **Debugging and Tracing with LangSmith:** Leveraged LangSmith for debugging and tracking API call executions.
12. **Authentication Service Communication:** Established communication with the authentication service.
13. **User Response Optimization:** Enhanced user response mechanism by transitioning from `invoke()` to `stream()`.

## Design of workflow
The data processing workflow is comprised of several sequential stages: 
![Service Architecture](https://github.com/gustaveroussy/PipelineAgentService/blob/main/img/PipelineWorkflow.jpg)

Each stage is characterized by a set of possible states, and the workflow progresses through these stages and states according to defined transition rules: 
![Service Architecture](https://github.com/gustaveroussy/PipelineAgentService/blob/main/img/StageWorkflow.jpg)

