import re
from dataclasses import dataclass
from typing import Optional

from core.config import FOLLOWUP_STRONG_KWS, REFER_KWS, YES_KWS, NO_KWS

@dataclass
class Intent:
    type: str
    number: str = ""
    reason: str = ""
    deny_dial: bool = False


class IntentRouter:
    """
    统一意图判定：
    - 仅负责识别，不处理业务
    """
    def __init__(self, matcher, number_converter, *, closing_kws, transfer_to_human_kws, followup_kws, llm_intent=None):
        self.matcher = matcher
        self.number_converter = number_converter
        self.closing_kws = closing_kws
        self.transfer_to_human_kws = transfer_to_human_kws
        self.followup_kws = followup_kws
        self.llm_intent = llm_intent

    @staticmethod
    def _has_any(text: str, kws) -> bool:
        return any(k in text for k in kws)

    @staticmethod
    def _has_refer(text: str) -> bool:
        return any(r in text for r in REFER_KWS)

    @staticmethod
    def _extract_digits(text: str) -> str:
        m = re.search(r"\d{5,12}", text or "")
        return m.group(0) if m else ""

    @staticmethod
    def _match_natural_confirm(text: str) -> Optional[str]:
        """使用正则匹配自然的确认表达"""
        if not text:
            return None
            
        # 肯定表达的正则模式
        yes_patterns = [
            r'嗯+.{0,3}(好|行|可以|要|转)',           # "嗯嗯好" "嗯行" "嗯可以转"
            r'(那就|那|就).{0,5}(转|接|好)',          # "那就转吧" "那转接" "就转吧"
            r'(没问题|OK|ok|可以的)',                 # "没问题" "OK" "可以的"
            r'(麻烦|拜托|劳烦).{0,5}转',              # "麻烦转一下" "拜托转接"
            r'(好的?|行).{0,3}(转|接)',              # "好的转" "行，转接"
            r'(成|中|得).{0,2}(转|接|好)',           # "成，转吧" "中，好的"
            r'(要得|好嘞|好咧|好滴)',                # "要得" "好嘞"
        ]
        
        # 否定表达的正则模式  
        no_patterns = [
            r'(算了|不用了|先不).{0,5}(转|接)',       # "算了不转" "不用了" "先不转"
            r'我(自己|先).{0,3}(打|记|联系)',         # "我自己打" "我先记下"
            r'(谢谢|多谢).{0,3}不用',                # "谢谢不用了" "多谢不用"
            r'(暂时|先|等等).{0,3}不',               # "暂时不用" "先不转" "等等不用"
            r'(记住了|知道了|明白了)',               # "我记住了" "知道了"
            r'(就这样|先这样).{0,2}吧?',             # "就这样吧" "先这样"
        ]
        
        for pattern in yes_patterns:
            if re.search(pattern, text):
                return "YES"
                
        for pattern in no_patterns:
            if re.search(pattern, text):
                return "NO"
                
        return None

    @staticmethod
    def _match_natural_query(text: str) -> bool:
        """匹配自然的查询表达"""
        if not text:
            return False
            
        query_patterns = [
            r'我想(知道|了解|问问).{0,10}(电话|号码|联系方式)',    # "我想知道张三的电话"
            r'能(告诉我|说说).{0,10}怎么联系',                   # "能告诉我怎么联系张三"
            r'.{0,10}(在哪个|哪个).{0,5}(部门|科室)',           # "张三在哪个部门"
            r'.{0,10}那边怎么(联系|找|打电话)',                 # "张三那边怎么联系"
            r'有.{0,10}的(联系方式|电话|号码)吗',               # "有张三的联系方式吗"
            r'怎么(找|联系|打给).{0,10}',                       # "怎么联系张三"
            r'.{0,10}的(联系方式|电话|号码)是(什么|多少)',       # "张三的电话是多少"
            r'(联系|找).{0,10}怎么办',                         # "联系张三怎么办"
        ]
        
        for pattern in query_patterns:
            if re.search(pattern, text):
                return True
        return False

    @staticmethod  
    def _match_natural_followup(text: str) -> bool:
        """匹配自然的追问表达"""
        if not text:
            return False
            
        followup_patterns = [
            r'(他|她|这个人|那个人).{0,5}还有.{0,5}(电话|号码|联系方式)',  # "他还有其他电话吗"
            r'还有.{0,3}(什么|啥|其他).{0,5}(电话|号码|联系方式)',      # "还有什么电话"
            r'有没有.{0,5}(其他|别的).{0,5}(电话|号码|联系方式)',      # "有没有其他电话"
            r'(其他|别的|另外).{0,5}(电话|号码|联系方式)',            # "其他电话号码"
            r'(他|她)的.{0,5}(手机|军线|办公|宿舍).{0,3}(电话|号码)',  # "他的手机号码"
        ]
        
        for pattern in followup_patterns:
            if re.search(pattern, text):
                return True
        return False

    def detect(self, asr: str, *, in_dial_confirm: bool, in_followup: bool) -> Intent:
        t = (asr or "").strip()
        if not t:
            return Intent("UNKNOWN", reason="empty")

        # 预先判断此句中是否包含明确“否定转接”的意图，用于复合意图
        natural_confirm = self._match_natural_confirm(t)
        has_deny = (natural_confirm == "NO") or self._has_any(t, NO_KWS)

        # 规则优先：转人工
        if self._has_any(t, self.transfer_to_human_kws):
            return Intent("TRANSFER_TO_HUMAN", reason="to_human")

        # 任何状态下，只要识别出纯粹有效的电话号码段，皆判定为 DIRECT_NUMBER 意图
        has_num, num = self.number_converter.has_valid_phone_number(t)
        if has_num:
            return Intent("DIRECT_NUMBER", number=num, reason="direct_number", deny_dial=has_deny)

        # 处于转接确认时：优先识别“追问/新查询”，否则走确认逻辑
        if in_dial_confirm:
            # 0) 新增：正则匹配自然表达的追问
            if self._match_natural_followup(t):
                return Intent("FOLLOWUP", reason="natural_followup", deny_dial=has_deny)
            
            # 1) 追问优先：指代词 + 号码相关词 / 强追问词
            if self._has_any(t, FOLLOWUP_STRONG_KWS) or (
                self._has_refer(t) and self._has_any(t, self.followup_kws)
            ):
                return Intent("FOLLOWUP", reason="dial_to_followup", deny_dial=has_deny)
            # 2) 新增：正则匹配自然表达的查询
            if self._match_natural_query(t):
                return Intent("NEW_QUERY", reason="natural_query", deny_dial=has_deny)
                
            # 3) 新查询优先：明显查询动作（避免误匹配"没问题"等词）
            query_keywords = ["查", "找", "帮我查", "再给我查", "我要找"]
            question_patterns = ["问一下", "问问", "请问", "我问"]  # 更精确的"问"相关匹配
            
            if (any(k in t for k in query_keywords) or 
                any(p in t for p in question_patterns)):
                return Intent("NEW_QUERY", reason="dial_to_new_query", deny_dial=has_deny)
                
            # 4) 新增：正则匹配自然表达的确认
            if natural_confirm == "YES":
                return Intent("DIAL_CONFIRM", reason="natural_confirm_yes")
            elif natural_confirm == "NO":
                return Intent("DIAL_CONFIRM", reason="natural_confirm_no")
                
            # 5) 明确肯定/否定，走确认逻辑
            if self._has_any(t, NO_KWS):
                return Intent("DIAL_CONFIRM", reason="dial_confirm_no")
            if self._has_any(t, YES_KWS):
                return Intent("DIAL_CONFIRM", reason="dial_confirm_yes")
                
            # 4) 其余交给 LLM 判 NEW_QUERY / FOLLOWUP / CLOSING
            if self.llm_intent:
                try:
                    llm_label = self.llm_intent.predict(t)
                    if llm_label in {"NEW_QUERY", "FOLLOWUP", "CLOSING"}:
                        return Intent(llm_label, reason=f"llm_{llm_label.lower()}", deny_dial=has_deny)
                except Exception:
                    pass
            return Intent("DIAL_CONFIRM", reason="dial_confirm")

        # 强结束语优先（避免被 LLM 误判为新查询）
        if self._has_any(t, self.closing_kws):
            return Intent("CLOSING", reason="closing_strong")

        # 新增：正则匹配自然查询表达（在LLM之前，作为快速路径）
        if self._match_natural_query(t):
            return Intent("NEW_QUERY", reason="natural_query_main")

        # LLM 主判：处理 NEW_QUERY / FOLLOWUP / CLOSING（优先于模板）
        if self.llm_intent:
            try:
                llm_label = self.llm_intent.predict(t)
                if llm_label in {"NEW_QUERY", "FOLLOWUP", "CLOSING"}:
                    return Intent(llm_label, reason=f"llm_{llm_label.lower()}")
            except Exception:
                pass

        # 模板兜底：命中新模板且不是指代词句
        matched_template = self.matcher.find_longest_match(t)
        if matched_template and not self._has_refer(t):
            return Intent("NEW_QUERY", reason="new_template")

        # 规则兜底：追问关键词
        if in_followup:
            # 新增：正则匹配自然追问表达
            if self._match_natural_followup(t):
                return Intent("FOLLOWUP", reason="natural_followup_main")
                
            if self._has_any(t, FOLLOWUP_STRONG_KWS):
                return Intent("FOLLOWUP", reason="followup_strong")
            if self._has_refer(t) and self._has_any(t, self.followup_kws):
                return Intent("FOLLOWUP", reason="followup_refer")

        # 规则兜底：结束语
        if self._has_any(t, self.closing_kws):
            return Intent("CLOSING", reason="closing")

        return Intent("UNKNOWN", reason="fallback")
