#!/usr/bin/env python3
"""
Send a single HANGUP message to MQ.
"""

import sys

# Add common path for RabbitMQ helper
sys.path.append("../../common")

try:
    from rabbitmq import RabbitMQ
except ImportError as exc:
    print(f"RabbitMQ import failed: {exc}")
    raise SystemExit(1)


def main() -> None:
    channel = sys.argv[1] if len(sys.argv) > 1 else "C0"
    mq = RabbitMQ()
    message = f"HANGUP:CHANNEL={channel}:PHONE=None"
    mq.publish(message)
    print(f"Sent: {message}")


if __name__ == "__main__":
    main()
