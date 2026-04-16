import sys
sys.path.append(r'D:\\AI114\\code\\common') 
import json
from rabbitmq import RabbitMQ 
mq = RabbitMQ()
def tts_and_save(requestID, sysfilename, channelNumber_id, TELE_CODE,text):
    try:
        message = (
            f"INTE_MSG:"
            f"CHANNEL={channelNumber_id}:"
            f"SEQ={requestID}:"
            f"FILE={sysfilename}:"
            f"PHONE={TELE_CODE}:"
            f"TEXT={text}:"
        )
        mq.publish(message)
        print("已发送到MQTTS")
    finally:
        mq.close()
    print("已发送到MQTTS")

if __name__ == '__main__':
    tts_and_save(
        requestID=3,
        sysfilename="5555555555555555555555555555.wav",
        channelNumber_id=0,
        TELE_CODE=15665465874,
        text="""
       好的，你要的是南疆军区的总机，号码是：985269，985269，需要我直接帮你转接过去吗。。
        """,
    )
   
