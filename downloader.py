import logging, requests, requests.adapters, queue, threading, os, random, time


def download_retry(requests_session, url, retry_num=1, max_retries=5):
    try:
        return requests_session.get(url).content
    except Exception:
        logging.exception("Exception downloading from url {}".format(url))
        if max_retries is None:
            raise
        elif retry_num > max_retries:
            logging.info("attempt {} failed, giving up".format(retry_num))
            raise
        else:
            sleep_time = random.choice(range(20,50))
            logging.info("attempt {} failed, sleeping {} seconds and retrying".format(retry_num, sleep_time))
            time.sleep(sleep_time)
            return download_retry(requests_session, url, retry_num+1)


def start_downloader(poolsize, numthreads, worker=None, max_retries=None):
        session = requests.session()
        session.mount("http://", requests.adapters.HTTPAdapter(pool_connections=poolsize, pool_maxsize=poolsize))
        session.mount("https://", requests.adapters.HTTPAdapter(pool_connections=poolsize, pool_maxsize=poolsize))
        q = queue.Queue()
        threads = []
        def thread_worker():
            while True:
                item = q.get()
                if item is None:
                    break
                # if worker callback is provided, it must return True to override the default functionality
                if not worker or not worker(item, session):
                    url, filepath = item
                    if not os.path.exists(filepath):
                        logging.info("Downloading {} -> {}".format(url, filepath))
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        with open(filepath, "wb") as f:
                            content = download_retry(session, url, max_retries=max_retries)
                            f.write(content)
                q.task_done()
        for i in range(numthreads):
            t = threading.Thread(target=thread_worker)
            t.start()
            threads.append(t)
        return q, threads


def stop_downloader(worker_queue, threads, numthreads):
    # block until all tasks are done
    worker_queue.join()
    # stop workers
    for i in range(numthreads):
        worker_queue.put(None)
    for t in threads:
        t.join()

