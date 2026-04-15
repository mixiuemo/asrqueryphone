#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发发送MQ测试消息（默认3条）
用于验证多ASR实例是否并发消费共享队列。
"""

import sys
import threading
from datetime import datetime

sys.path.append('../../common')
from rabbitmq import RabbitMQ


def now_ms():
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]


def build_message(idx):
    channel = f"C{idx - 1}"
    seq = f"{idx:03d}"
    phone = f"1380013800{idx - 1}"
    user_circuit = f"100{idx}"
    filename = f"{idx}.wav"
    return (
        f"RECORD:CHANNEL={channel}:SEQ={seq}:PHONE={phone}:"
        f"USERCIRCUIT={user_circuit}:FILE={filename}"
    )


def publish_one(idx, barrier):
    msg = build_message(idx)
    mq = RabbitMQ()
    try:
        mq.connect()
        barrier.wait()  # 所有线程就绪后同时发
        print(f"[{now_ms()}] SEND-{idx}: {msg}")
        ok = mq.publish(msg.encode('utf-8'))
        print(f"[{now_ms()}] ACK -{idx}: {ok}")
    except Exception as e:
        print(f"[{now_ms()}] ERR -{idx}: {e}")
    finally:
        try:
            mq.close()
        except Exception:
            pass


def main():
    count = 3
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
    if count <= 0:
        raise ValueError("count must be > 0")

    print(f"[{now_ms()}] start concurrent publish, count={count}")
    barrier = threading.Barrier(count)
    threads = []
    for i in range(1, count + 1):
        t = threading.Thread(target=publish_one, args=(i, barrier), daemon=False)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()
    print(f"[{now_ms()}] done")


if __name__ == '__main__':
    main()
