import os
from rq import Queue, Worker
from redis import Redis
import multiprocessing
from time import sleep
from rq.registry import StartedJobRegistry, FinishedJobRegistry


def start_worker(queue_name):
    """启动 RQ worker 的函数"""
    redis_conn = Redis()
    q = Queue(queue_name, connection=redis_conn)
    worker = Worker(q, connection=redis_conn)
    # print(f"Worker process {os.getpid()} started, listening to queues: {queue_name}") # 打印进程 ID 和监听的队列
    worker.work()
    return 

if __name__ == '__main__':
    queue_name = "pipeline"

    print(f"Establish Redis connection")
    redis_conn = Redis()

    print(f"Create a redis queue")
    q = Queue(queue_name, connection=redis_conn)  # no args implies the default queue
    q.empty() # 清空队列

    print(q.get_jobs()) # 打印队列中的任务

    print("Start worker processes")
    num_workers = 2
    processes = []
    for i in range(num_workers):
        # 创建 worker 进程，并传递队列名称
        process = multiprocessing.Process(target=start_worker, args=(queue_name,))
        process.daemon = True
        processes.append(process)
        process.start() # 启动进程

    # Delay execution of count_words_at_url('http://nvie.com')
    print("Enqueue jobs")
    jobs = [ q.enqueue(sleep, 5) for i in range(3) ] 

    for i in range(15):
        for job in q.get_jobs():
            print(f"Job {job.id} is in status {job.get_status()}")

        # 查看正在运行中的任务
        started_registry = StartedJobRegistry(q.name, connection=q.connection)
        started_job_ids = started_registry.get_job_ids()
        print("Started jobs:", started_job_ids)

        # 查看已经完成的任务
        finished_registry = FinishedJobRegistry(q.name, connection=q.connection)
        finished_job_ids = finished_registry.get_job_ids()
        print("Finished jobs:", finished_job_ids)

        # for job in jobs:
        #     print(f"Job {job.id} is in status {job.get_status()}")

        sleep(2)

    print("==============================")
    print(q.get_jobs()) # 打印队列中的任务