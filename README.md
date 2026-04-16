需要安装MQ消息服务
需要安装MYSQL数据库
系统默认读取MYSQL数据库中的rgt数据库中的tele表，需要创建tele表

admin端为系统的运行管理端，包含前端react,后端python

asr端包含
  语音识别端：需要下载模型并放入identifyPro目录下面的iic目录下
  https://modelscope.cn/models/iic/speech_paraformer-large-contextual_asr_nat-zh-cn-16k-common-vocab8404

  交互逻辑端：需要下载LLM放入到Interaction目录下面的data目录中
  https://modelscope.cn/models/Qwen/Qwen3-0.6B

tts语音合成端需要下载模型放入到tts目录下即可
https://modelscope.cn/models/AI-ModelScope/Kokoro-82M-v1.1-zh


整个流程都是需要通过MQ收发消息来处理：
  语音卡端>asr识别>业务逻辑交互>语音合成端>语音卡端


common为配置类，读取配置文件 config.ini是具体的配置项
