from __future__ import annotations

from typing import List
import re

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


class LLMIntentClassifier:
    def __init__(self, model_path: str, device: str = "cuda"):
        self.model_path = model_path
        self.device = device
        self.labels = [
            "DIAL_CONFIRM",
            "FOLLOWUP",
            "DISAMBIG",
            "DIRECT_NUMBER",
            "NEW_QUERY",
            "CLOSING",
            "TRANSFER_TO_HUMAN",
            "UNKNOWN",
        ]
        self.examples = [
            ("帮我找一下张三，谢谢", "NEW_QUERY"),
            ("查一下技术部李四的电话", "NEW_QUERY"),
            ("不用了谢谢，你再给我查下翠园", "NEW_QUERY"),
            ("不用转接了，帮我查一下李四", "NEW_QUERY"),
            ("不用了谢谢，你再给我查下他那个手机号", "FOLLOWUP"),
            ("不用了谢谢，帮我查下他还有没有别的号码", "FOLLOWUP"),
            ("他还有别的号码吗", "FOLLOWUP"),
            ("他那个手机号是多少", "FOLLOWUP"),
            ("不用了，谢谢", "CLOSING"),
            ("好了再见", "CLOSING"),
            ("可以，帮我转接", "DIAL_CONFIRM"),
            ("不用转接了", "DIAL_CONFIRM"),
            ("13800138000是谁的电话", "DIRECT_NUMBER"),
            ("转人工客服", "TRANSFER_TO_HUMAN"),
            ("我找技术部的张三", "DISAMBIG"),
        ]
        self.refer_strong = ["他", "她", "那位", "这位", "对方", "此人"]
        self.phone_kws = ["电话", "号码", "手机号", "手机", "军线", "办公", "内线", "宿舍"]
        self.query_kws = ["查", "找", "问", "帮我查", "再给我查", "我要找"]
        self.name_stop = {
            "那个", "这位", "那位", "对方", "此人", "电话", "号码", "手机号", "手机",
            "军线", "办公", "内线", "宿舍", "查询", "查", "找", "帮我", "再给我", "我要",
        }

        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            dtype=torch.float16,
            trust_remote_code=True,
        ).to(device)

    def _build_prompt(self, utterance: str) -> str:
        examples = "\n".join([f"用户话语：{u}\n标签：{y}" for u, y in self.examples])
        return (
            "你是意图分类器，只能输出一个标签。\n"
            f"标签集合：{', '.join(self.labels)}\n"
            "规则：\n"
            "0) 注意：ASR 可能把人名/单位/职位识别成普通词或错误词（如“丁薇”→“定位”），当句子结构明显是“查某人/某单位/某职位的电话”，即使名字识别异常也优先判为 NEW_QUERY。\n"
            "1) 如果句子包含“他/她/这位/那位/对方”等指代词，且包含“电话/号码/手机号/手机/军线/办公/内线/宿舍”等号码相关词，优先判定为 FOLLOWUP。\n"
            "2) 否则如果句子包含“查/找/问/帮我查/再给我查/我要找”等查询动作，即使包含“谢谢/不用了”，也优先判定为 NEW_QUERY。\n"
            "示例：\n"
            f"{examples}\n"
            f"用户话语：{utterance}\n"
            "只输出标签："
        )

    def _post_process(self, utterance: str, label: str) -> str:
        # 强指代 + 号码词 => 追问
        if any(k in utterance for k in self.refer_strong) and any(k in utterance for k in self.phone_kws):
            return "FOLLOWUP"
        if any(k in utterance for k in self.query_kws):
            return "NEW_QUERY"
        return label

    def predict(self, utterance: str) -> str:
        utterance = (utterance or "").strip()
        if not utterance:
            return "UNKNOWN"
        prompt = self._build_prompt(utterance)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=8,
            do_sample=False,
        )
        decoded = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        label = decoded.split("只输出标签：", 1)[-1].strip().splitlines()[0]
        if label not in self.labels:
            label = "UNKNOWN"
        return self._post_process(utterance, label)
