"""
新版交互主程序 main.py
- 保留 runMain.py 的 ASR消息接收 / MQ发送 / 拼音模板匹配
- 采用灵活状态机设计，找到唯一结果统一询问是否转接
- 所有配置统一在 core/config.py 管理
"""
import re
import random
import sys
import uuid
import time
import signal
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

sys.path.append('../../common')
from rabbitmq import RabbitMQ
from utils.loggeruitls import Logger
from utils.number_converter import NumberConverter
from utils.phone_location import PhoneLocation
from utils.websocket_client import websocket_client

# 从 runMain.py 复用的核心类（拼音匹配 / 电话类型识别）
from core.matcher import PhoneTypeExtractor, PinyinMatcher, load_global_configs

# 所有配置统一从 core/config.py 读取
from core.config import (
    MSG_ASK_DIAL, MSG_DIAL_YES,
    MSG_NO_RESULT, MSG_NO_RESULT_2ND, MSG_NO_RESULT_3RD, MSG_NO_MORE_PHONE, MSG_NOT_CLEAR,
    MSG_DISAMBIG_FAIL, MSG_NO_PERMISSION,
    YES_KWS, NO_KWS, CLOSING_KWS, JUMP_KWS, FOLLOWUP_KWS, 
    TRANSFER_TO_HUMAN_KWS, PHONE_TYPE_PRIORITY, PHONE_TYPE_NAME_MAP,
    PHONE_TYPE_DISPLAY, ASK_SPECIFIC_PHONE,
    MSG_RESULT_TEMPLATES,
    MSG_MULTI_RESULT_TEMPLATES, MSG_DISAMBIG_MORE_TEMPLATES,
    MSG_DIRECT_NUMBER_FOUND_TEMPLATES, MSG_DIRECT_NUMBER_NOT_FOUND_TEMPLATES,
    MSG_FAREWELL_TEMPLATES, MSG_NO_TRANSFER_TEMPLATES, MSG_NO_TRANSFER_FOLLOWUP_TEMPLATES,
    MSG_NO_TRANSFER_THEN_QUERY_PREFIX_TEMPLATES,
)
from core.intent_router import IntentRouter

from flask import Flask, jsonify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

log = Logger()
app = Flask(__name__)

# ──────────────────────────────────────────────
# 会话状态（精简、清晰）
# ──────────────────────────────────────────────
@dataclass
class Session:
    channel_id:   str
    request_id:   str
    caller_number: str = ""
    user_circuit:  str = ""
    caller_level: int = 1

    # 来电人信息（权限查询用）
    call_name: str = ""
    call_job:  str = ""
    call_unit: str = ""

    # 当前正在处理的候选列表（多结果消歧用）
    candidates: List[dict] = field(default_factory=list)

    # 已确认的单条结果（等待转接确认）
    confirmed: Optional[dict] = None
    # 是否处于"等待转接确认"
    dial_confirm: bool = False
    # 转接确认超时（秒）
    dial_expires: float = 0.0

    # 号码追问模式
    followup_person_key: tuple = field(default_factory=tuple)
    followup_grouped:    dict  = field(default_factory=dict)   # cat -> [records]
    followup_spoken:     set   = field(default_factory=set)    # 已播报的电话号码
    followup_expires:    float = 0.0
    just_denied_dial:    bool  = False  # 刚拒绝转接（追问其他号码时话术要调整）

    response_prefix:     str   = ""     # 用于拼接带前后衔接的播报语句

    # 最近一次触发查询的原始 ASR 文本（用于 followup 时精准找同人号码）
    last_query_text: str = ""

    # 台位类兜底确认（例如仅有总机时询问是否接受）
    role_fallback_confirm: bool = False
    
    # 连续查询失败计数（用于主动提示和自动转人工）
    failed_query_count: int = 0

    # 累计日志
    user_log: str = ""
    sys_log:  str = ""
    wav_log:  str = ""
    sys_wav_log: str = ""

    def in_disambiguation(self) -> bool:
        return bool(self.candidates)

    def in_dial_confirm(self) -> bool:
        return self.dial_confirm and time.time() < self.dial_expires

    def in_followup(self) -> bool:
        return bool(self.followup_person_key)

    def clear_query(self):
        """清空本轮查询上下文（保留通话元数据）"""
        self.candidates      = []
        self.confirmed       = None
        self.dial_confirm    = False
        self.dial_expires    = 0.0
        self.followup_person_key = tuple()
        self.followup_grouped    = {}
        self.followup_spoken     = set()
        self.followup_expires    = 0.0
        self.just_denied_dial    = False
        self.role_fallback_confirm = False
        # 注意：failed_query_count 不清空，累计到转人工为止


# ──────────────────────────────────────────────
# 文件热重载监听器
# ──────────────────────────────────────────────
class JSONFileHandler(FileSystemEventHandler):
    def __init__(self, matcher: PinyinMatcher):
        self.matcher = matcher
        self._last: Dict[str, float] = {}

    def on_modified(self, event):
        if event.is_directory:
            return
        p = event.src_path
        if not p.endswith(('phone_database.json', 'query_templates.json', 'query_templates_no_tone.json')):
            return
        now = time.time()
        if now - self._last.get(p, 0) < 1:
            return
        self._last[p] = now
        log.info(f"检测到文件变化: {p}，重新加载…")
        try:
            time.sleep(0.5)
            self.matcher.phone_database = self.matcher._load_phone_database()
            self.matcher.query_templates = self.matcher._load_query_templates()
            self.matcher.query_templates_no_tone = self.matcher._load_query_templates(
                "./data/query_templates_no_tone.json"
            )
            self.matcher.template_set = set(self.matcher.query_templates)
            self.matcher.template_set_no_tone = set(self.matcher.query_templates_no_tone)
            self.matcher._template_index, self.matcher._template_max_len = self.matcher._build_template_index(
                self.matcher.template_set
            )
            self.matcher._template_index_no_tone, self.matcher._template_max_len_no_tone = self.matcher._build_template_index(
                self.matcher.template_set_no_tone
            )
            self.matcher.rebuild_unit_lexicon()
            log.info("数据重新加载完成")
        except Exception as e:
            log.error(f"重新加载失败: {e}")


# ──────────────────────────────────────────────
# 工具函数（所有关键词均来自 core/config.py）
# ──────────────────────────────────────────────

def _is_yes(text: str) -> bool:
    """肯定回答：先排除否定词，避免'不对'被'对'误命中"""
    t = text.strip()
    if _is_no(t):
        return False
    return any(kw in t for kw in YES_KWS)

def _is_no(text: str) -> bool:
    t = text.strip()
    return any(kw in t for kw in NO_KWS)

def _is_closing(text: str) -> bool:
    """用户表示'没有其他需求了'"""
    return any(kw in text for kw in CLOSING_KWS)

def _is_transfer_to_human(text: str) -> bool:
    return any(kw in text for kw in TRANSFER_TO_HUMAN_KWS)

def _get_specific_phone_category(text: str) -> str:
    """用户明确要求某类电话，返回内部 category（military/mobile/office/dorm），否则返回空串"""
    # 优先识别“手机/移动”类，避免被“电话/号码”误判成办公座机
    if text:
        if ("军" in text or "军用" in text or "军线" in text) and "手机" in text:
            return "military"
        if any(k in text for k in ["手机", "手机号", "手机号码", "移动"]):
            return "mobile"
    for cat, kws in ASK_SPECIFIC_PHONE.items():
        if any(kw in text for kw in kws):
            return cat
    return ""

def _phone_type_category(telephone_type: str) -> str:
    """telephoneType 字段 → 内部 category"""
    t = telephone_type or ""
    if t in PHONE_TYPE_NAME_MAP:
        return PHONE_TYPE_NAME_MAP[t]
    return "other"

def _format_result(r: dict) -> str:
    unit  = (r.get('UNIT') or '').strip()
    name  = (r.get('PERSONNEL') or '').strip()
    job   = (r.get('JOB') or '').strip()
    phone = (r.get('TELE_CODE') or '').strip()
    if unit == name:
        desc = f"{unit}{job}"
    elif name == job:
        desc = f"{unit}的{name}"
    else:
        desc = f"{unit}的{name}{job}"
    tmpl = random.choice(MSG_RESULT_TEMPLATES) if MSG_RESULT_TEMPLATES else "您好，{desc}的电话是：{phone}，{phone}。"
    return tmpl.format(desc=desc, phone=phone)

def _choose_template(templates: list, **kwargs) -> str:
    if not templates:
        return ""
    return random.choice(templates).format(**kwargs)

def _group_by_category(records: List[dict]) -> Dict[str, List[dict]]:
    grouped: Dict[str, List[dict]] = {cat: [] for cat in PHONE_TYPE_PRIORITY}
    for r in records:
        cat = _phone_type_category((r.get('telephoneType') or '').strip())
        grouped.setdefault(cat, []).append(r)
    return grouped

def _pick_by_priority(grouped: Dict[str, List[dict]], spoken: set) -> Optional[dict]:
    """按优先级顺序取第一个未播报的号码"""
    for cat in PHONE_TYPE_PRIORITY:
        for r in grouped.get(cat, []):
            if (r.get('TELE_CODE') or '').strip() not in spoken:
                return r
    return None

def _pick_by_category(grouped: Dict[str, List[dict]], cat: str, spoken: set) -> Optional[dict]:
    """取指定 category 中第一个未播报的号码"""
    for r in grouped.get(cat, []):
        if (r.get('TELE_CODE') or '').strip() not in spoken:
            return r
    return None

def _best_by_priority(records: List[dict], asr: str = "") -> Optional[dict]:
    """同人多号时按优先级选一个（可结合用户类型意图）"""
    if not records:
        return None
    requested_cat = _get_specific_phone_category(asr)
    if requested_cat:
        if requested_cat == "military" and any(k in (asr or "") for k in ["手机", "手机号", "移动"]):
            priority_list = ["military", "mobile", "office", "dorm", "other"]
        else:
            priority_list = [requested_cat] + [c for c in PHONE_TYPE_PRIORITY if c != requested_cat]
    else:
        priority_list = PHONE_TYPE_PRIORITY
    priority = {cat: idx for idx, cat in enumerate(priority_list)}

    def rank(r: dict) -> int:
        cat = _phone_type_category((r.get('telephoneType') or '').strip())
        return priority.get(cat, len(priority))

    return sorted(records, key=rank)[0]


# ──────────────────────────────────────────────
# 核心管理器
# ──────────────────────────────────────────────
class MainManager:
    def __init__(self):
        self.sessions:         Dict[str, Session] = {}
        self.phone_extractor   = PhoneTypeExtractor()
        self.number_converter  = NumberConverter()
        self.matcher           = PinyinMatcher()
        self.mq                = RabbitMQ()
        self.llm_intent        = None
        try:
            from core.llm_intent import LLMIntentClassifier
            self.llm_intent = LLMIntentClassifier(model_path="data/qwen3-0.6B")
            log.info("LLM 意图模型已加载")
        except Exception as e:
            log.error(f"LLM 意图模型加载失败: {e}")
        self.intent_router     = IntentRouter(
            self.matcher,
            self.number_converter,
            closing_kws=CLOSING_KWS,
            transfer_to_human_kws=TRANSFER_TO_HUMAN_KWS,
            followup_kws=FOLLOWUP_KWS,
            llm_intent=self.llm_intent,
        
        )
        self._start_file_watcher()

    @staticmethod
    def _get_level(r: Optional[dict], default: int = 1) -> int:
        if not r:
            return default
        v = r.get('queryPermission', default)
        try:
            if v is None:
                return default
            if isinstance(v, bool):
                return int(v)
            return int(str(v).strip() or default)
        except Exception:
            return default

    @staticmethod
    def _allowed(caller_level: int, target: dict) -> bool:
        return caller_level >= MainManager._get_level(target, default=1)

    # ── 文件监听 ──────────────────────────────
    def _start_file_watcher(self):
        try:
            handler       = JSONFileHandler(self.matcher)
            self._observer = Observer()
            self._observer.schedule(handler, './data', recursive=False)
            self._observer.start()
            log.info("文件监听器已启动，监听 ./data 目录")
        except Exception as e:
            log.error(f"启动文件监听器失败: {e}")

    def stop(self):
        if hasattr(self, '_observer'):
            self._observer.stop()
            self._observer.join()

    # ── 入口：处理 ASR 消息 ───────────────────
    def handle(self, data: Dict[str, Any]):
        channel_id = data.get('channel_id', '')
        if not channel_id:
            log.error("消息缺少 channel_id，跳过")
            return

        if channel_id not in self.sessions:
            self._new_session(data)
        else:
            self._continue_session(data)

    # ── 新会话 ────────────────────────────────
    def _new_session(self, data: Dict[str, Any]):
        channel_id    = data['channel_id']
        s = Session(
            channel_id    = channel_id,
            request_id    = data.get('request_id', ''),
            caller_number = data.get('caller_number', ''),
            user_circuit  = data.get('user_circuit', ''),
        )
        self.sessions[channel_id] = s
        self._lookup_caller(s)
        log.info(f"新会话: channel={channel_id}, caller={s.caller_number}")
        filename = data.get('filename', '')
        if filename:
            s.wav_log += filename + "##"
        self._process(s, data.get('asr_result', ''))

    # ── 续谈 ──────────────────────────────────
    def _continue_session(self, data: Dict[str, Any]):
        channel_id = data['channel_id']
        s = self.sessions[channel_id]
        # 更新 request_id / user_circuit（每轮可能变化）
        s.request_id   = data.get('request_id', s.request_id)
        s.user_circuit = data.get('user_circuit', s.user_circuit)
        filename = data.get('filename', '')
        if filename:
            s.wav_log += filename + "##"
        asr = data.get('asr_result', '')
        log.info(f"续谈: channel={channel_id}, asr={asr!r}")
        self._process(s, asr)

    # ── 统一处理入口 ──────────────────────────
    def _process(self, s: Session, asr: str):
        asr = (asr or '').strip()
        s.user_log += asr + "##"

        # 台位类兜底确认优先处理（例如“库里只有总机，是否要这个”）
        if s.role_fallback_confirm:
            if _is_yes(asr):
                cand = s.candidates[0] if s.candidates else None
                s.role_fallback_confirm = False
                s.candidates = []
                if cand:
                    self._present_single(s, cand)
                else:
                    self._speak(s, MSG_NO_RESULT)
                    s.clear_query()
                return
            if _is_no(asr):
                self._speak(s, MSG_NO_MORE_PHONE)
                s.clear_query()
                return
            # 其他话术：退出确认，继续走正常意图
            s.role_fallback_confirm = False
            s.candidates = []

        # 多结果消歧优先处理，避免被意图识别抢走，但是需要拦截强退出指令
        if s.in_disambiguation():
            ambig_intent = self.intent_router.detect(asr, in_dial_confirm=False, in_followup=False)
            # if ambig_intent.type in ["CLOSING", "TRANSFER_TO_HUMAN", "NEW_QUERY"] and not ambig_intent.reason.startswith("new_template"):
            if ambig_intent.type in ["CLOSING", "TRANSFER_TO_HUMAN", "NEW_QUERY"]:
                # 如果用户在听候选列表时，说了明确的“退出”、“转人工”或者“帮我查别人”，则跳出消歧
                log.info(f"消歧状态中收到明确跳出指令: {ambig_intent.type}")
                s.candidates = []
                # 跳出消歧判断，继续往下走常规意图路由
            else:
                log.info(f"意图判定: type=DISAMBIG, reason=state_disambiguation, asr={asr!r}")
                self._handle_disambiguation(s, asr)
                return

        # 用户明确结束（优先于后续意图）
        # 但不要抢占“转接确认/台位兜底确认”等需要 YES/NO 的场景
        if _is_closing(asr) and (not s.in_dial_confirm()) and (not s.role_fallback_confirm):
            msg = _choose_template(MSG_FAREWELL_TEMPLATES)
            if msg:
                self._speak(s, msg)
            s.clear_query()
            return

        # 统一意图判定
        intent = self.intent_router.detect(
            asr,
            in_dial_confirm=s.in_dial_confirm(),
            in_followup=s.in_followup(),
        )
        log.info(f"意图判定: type={intent.type}, reason={intent.reason}, asr={asr!r}")

        if intent.type == "CLOSING":
            msg = _choose_template(MSG_FAREWELL_TEMPLATES)
            if msg:
                self._speak(s, msg)
            s.clear_query()
            return

        if intent.type == "TRANSFER_TO_HUMAN":
            self._handle_transfer_to_human(s)
            return

        if intent.type == "DIRECT_NUMBER":
            if getattr(intent, 'deny_dial', False) and s.in_dial_confirm():
                s.response_prefix = _choose_template(MSG_NO_TRANSFER_THEN_QUERY_PREFIX_TEMPLATES) or "好的，上一条先不转接。"
            s.dial_confirm = False
            s.confirmed = None
            s.just_denied_dial = False
            s.clear_query()
            self._handle_direct_number(s, asr, intent.number)
            return

        if intent.type == "NEW_QUERY":
            # 如果是由“不用了，查下李四”触发，补一句轻微衔接
            if getattr(intent, 'deny_dial', False) and s.in_dial_confirm():
                s.response_prefix = _choose_template(MSG_NO_TRANSFER_THEN_QUERY_PREFIX_TEMPLATES) or "好的，上一条先不转接。"

            # 退出追问/确认，直接新查询
            s.dial_confirm = False
            s.confirmed = None
            s.just_denied_dial = False
            s.clear_query()
            self._handle_query(s, asr)
            return

        if intent.type == "FOLLOWUP":
            if getattr(intent, 'deny_dial', False) and s.in_dial_confirm():
                # 设置刚刚拒绝了转接旗标，传递给 followup 调整话术
                s.just_denied_dial = True
            self._handle_followup(s, asr)
            return

        # 转接确认
        if s.in_dial_confirm():
            self._handle_dial_confirm(s, asr, intent)
            return

        # 空输入
        if not asr:
            self._speak(s, MSG_NOT_CLEAR)
            return

        # 默认：正常查询
        self._handle_query(s, asr)

    # ── 处理：正常查询 ────────────────────────
    def _handle_query(self, s: Session, asr: str):
        raw_results = self.matcher.find_matches(asr)
        raw_results = self.matcher.filter_results_by_unit_hint(raw_results, asr)
        # 权限过滤（等级制：caller >= target）
        results = [r for r in raw_results if self._allowed(s.caller_level, r)]
        if raw_results:
            for r in raw_results[:5]:
                name = (r.get('PERSONNEL') or '').strip()
                unit = (r.get('UNIT') or '').strip()
                lvl  = self._get_level(r, default=1)
                log.info(f"权限检查: caller_level={s.caller_level}, target_level={lvl}, target={unit}{name}")

        if not results:
            if raw_results:
                log.info("匹配到结果但无权限，返回无权限提示")
                self._speak(s, MSG_NO_PERMISSION)
                s.clear_query()
                return
            fallback = self.matcher.fallback_role_class_by_unit(asr)
            if fallback:
                unit_display, role_label, candidates = fallback
                allowed_candidates = [r for r in candidates if self._allowed(s.caller_level, r)]
                if not allowed_candidates:
                    log.info("台位兜底命中但无权限，返回无权限提示")
                    self._speak(s, MSG_NO_PERMISSION)
                    s.clear_query()
                    return
                s.candidates = allowed_candidates
                s.role_fallback_confirm = True
                s.last_query_text = asr
                self._speak(s, f"号码库里只有{unit_display}的{role_label}，是否要这个？")
                return
            # 连续失败计数 +1
            s.failed_query_count += 1
            log.info(f"查询失败，当前连续失败次数：{s.failed_query_count}")
            
            # 根据失败次数给出不同提示
            if s.failed_query_count == 1:
                msg = MSG_NO_RESULT
            elif s.failed_query_count == 2:
                msg = MSG_NO_RESULT_2ND
            else:  # >= 3次，自动转人工
                msg = MSG_NO_RESULT_3RD
                self._speak(s, msg)
                log.info(f"连续查询失败{s.failed_query_count}次，自动转人工")
                self._handle_transfer_to_human(s)
                # s 在 _handle_transfer_to_human 内部可能已经被销毁。此时应直接返回，不要再 clear_query 或修改 s。
                return
            
            self._speak(s, msg)
            s.clear_query()
            return

        # 查到了，重置失败计数
        if s.failed_query_count > 0:
            log.info(f"查询成功，重置失败计数（之前={s.failed_query_count}）")
            s.failed_query_count = 0

        # 同人去重：同单位+姓名+职位只保留一个号码（结合用户类型意图）
        grouped_by_person: Dict[tuple, List[dict]] = {}
        for r in results:
            k = (
                (r.get('UNIT') or '').strip(),
                (r.get('PERSONNEL') or '').strip(),
                (r.get('JOB') or '').strip(),
            )
            grouped_by_person.setdefault(k, []).append(r)
        if len(grouped_by_person) != len(results):
            merged: List[dict] = []
            for _, lst in grouped_by_person.items():
                best = _best_by_priority(lst, asr)
                if best:
                    merged.append(best)
            results = merged

        # 记录本次查询词（供消歧后 followup 使用）
        s.last_query_text = asr

        # 电话类型过滤（同一人多号时挑优先级最高的，其余存入 followup）
        results, notice = self._apply_type_preference(results, asr)

        if len(results) == 1:
            self._present_single(s, results[0], notice)
        else:
            self._present_multiple(s, results)

    # ── 处理：单条结果 ────────────────────────
    def _present_single(self, s: Session, r: dict, notice: str = ""):
        # 进入号码追问模式（缓存该人其他号码，直接从数据库取，不重查）
        self._enter_followup(s, r)
        msg = _format_result(r)
        if notice:
            msg += f"{notice}。"
        msg += MSG_ASK_DIAL
        s.confirmed    = r
        s.dial_confirm = True
        s.dial_expires = time.time() + 60.0
        self._speak(s, msg, tele_code=r.get('TELE_CODE', ''), switch_value=0)

    # ── 处理：多条结果 ────────────────────────
    def _present_multiple(self, s: Session, results: List[dict]):
        s.candidates = results
        s.clear_query()
        s.candidates = results  # clear_query 会清空，重新赋值
        opts = "；".join(
            f"{(r.get('UNIT') or '').strip()}的{(r.get('PERSONNEL') or '').strip()}{(r.get('JOB') or '').strip()}"
            for r in results[:5]
        )
        msg = _choose_template(MSG_MULTI_RESULT_TEMPLATES, opts=opts)
        if msg:
            self._speak(s, msg)

    # ── 处理：消歧 ────────────────────────────
    def _handle_disambiguation(self, s: Session, asr: str):
        # 翻篇检测：用户可能在找别人
        if any(kw in asr for kw in JUMP_KWS):
            s.clear_query()
            self._handle_query(s, asr)
            return

        # 先用中文+数字归一化筛选；若失败再回退拼音筛选。
        filtered = self._filter_candidates(s.candidates, asr)
        if not filtered:
            filtered = self._filter_candidates_by_pinyin(s.candidates, asr)
        # 若已收敛到同一人多号码，按优先级选一个进入单结果流程
        if filtered:
            filtered, _ = self._apply_type_preference(filtered, asr)

        if not filtered:
            self._speak(s, MSG_DISAMBIG_FAIL)
            return

        if len(filtered) == 1:
            s.candidates = []
            self._present_single(s, filtered[0])   # followup 直接从 DB 找同人号码
        else:
            s.candidates = filtered
            opts = "；".join(
                f"{(r.get('UNIT') or '').strip()}的{(r.get('PERSONNEL') or '').strip()}{(r.get('JOB') or '').strip()}"
                for r in filtered[:5]
            )
            msg = _choose_template(MSG_DISAMBIG_MORE_TEMPLATES, opts=opts)
            if msg:
                self._speak(s, msg)

    # ── 处理：转接确认 ────────────────────────
    def _handle_dial_confirm(self, s: Session, asr: str, intent: Optional[Any] = None):

        # 优先级3：明确肯定 (规则或正则捕获到 YES_KWS 或 natural confirm yes)
        is_yes = _is_yes(asr) or (intent and intent.type == "DIAL_CONFIRM" and intent.reason.endswith("yes"))
        if is_yes:
            r = s.confirmed
            if r:
                phone = PhoneLocation.format_dial_number(r.get('TELE_CODE') or '')
                s.sys_log += f"用户转接{phone}##"
                self._send_tts(s, "", "", phone, switch_value=1,
                               result_unit=(r.get('UNIT') or '').strip(),
                               result_name=(r.get('PERSONNEL') or '').strip(),
                               result_job=(r.get('JOB') or '').strip())
            s.clear_query()
            return

        # 优先级4：明确否定
        is_no = _is_no(asr) or (intent and intent.type == "DIAL_CONFIRM" and intent.reason.endswith("no"))
        if is_no:
            msg = _choose_template(MSG_NO_TRANSFER_TEMPLATES)
            if msg:
                self._speak(s, msg)
            # 标记"刚拒绝转接"，followup 时话术要调整
            s.just_denied_dial = True
            s.dial_confirm = False
            s.confirmed = None
            # 不清空 followup 状态，允许用户继续追问其他号码
            return

        # 优先级5：说了别的，退出确认、重新查询
        s.dial_confirm = False
        s.confirmed    = None
        self._handle_query(s, asr)

    # ── 处理：号码追问 ────────────────────────
    def _handle_followup(self, s: Session, asr: str):
        requested_cat = _get_specific_phone_category(asr)
        want_next     = any(kw in asr for kw in ["还有", "其他", "别的", "另一个"])
        # “还有其他电话吗”这类泛问不要被“电话”误判成办公类型
        if want_next and requested_cat == "office":
            requested_cat = ""

        if requested_cat:
            # 该类型号码已全部播报
            all_in_cat = s.followup_grouped.get(requested_cat, [])
            if all_in_cat and all((r.get('TELE_CODE') or '').strip() in s.followup_spoken for r in all_in_cat):
                self._speak(s, MSG_NO_MORE_PHONE)
                s.clear_query()
                return
            # 用户说“手机”时，优先军用手机/军线，其次移动手机
            if requested_cat == "military" and any(k in asr for k in ["手机", "手机号", "移动"]):
                priority_cats = ["military", "mobile"]
            else:
                priority_cats = [requested_cat]

            for cat in priority_cats:
                all_in_cat = s.followup_grouped.get(cat, [])
                allowed_in_cat = [
                    r for r in all_in_cat
                    if self._allowed(s.caller_level, r)
                    and (r.get('TELE_CODE') or '').strip() not in s.followup_spoken
                ]
                if allowed_in_cat:
                    self._speak_followup(s, allowed_in_cat[0])
                    return
                if all_in_cat:
                    # 有该类型号码但无权限
                    self._speak(s, MSG_NO_PERMISSION)
                    s.clear_query()  # 修复：清理状态，避免后续处理异常
                    return
            # 没有该类型，回退到下一个未播报的，并给出友好提示
            fallback = _pick_by_priority(s.followup_grouped, s.followup_spoken)
            if fallback:
                if not self._allowed(s.caller_level, fallback):
                    self._speak(s, MSG_NO_PERMISSION)
                    s.clear_query()  # 修复：清理状态，避免后续处理异常
                    return
                requested_name = PHONE_TYPE_DISPLAY.get(requested_cat, "该类型电话")
                fallback_cat   = _phone_type_category((fallback.get('telephoneType') or '').strip())
                fallback_name  = PHONE_TYPE_DISPLAY.get(fallback_cat, "")
                if fallback_name and fallback_cat != "other":
                    notice = f"{requested_name}没有查到，我先给您{fallback_name}号码"
                else:
                    notice = f"{requested_name}没有查到，我先给您另一个号码"
                self._speak_followup(s, fallback, notice)
                return
            self._speak(s, MSG_NO_MORE_PHONE)
            s.clear_query()
            return

        if want_next:
            # 按优先级寻找下一个未播报且有权限的号码
            for cat in PHONE_TYPE_PRIORITY:
                for r in s.followup_grouped.get(cat, []):
                    phone = (r.get('TELE_CODE') or '').strip()
                    if phone in s.followup_spoken:
                        continue
                    if not self._allowed(s.caller_level, r):
                        self._speak(s, MSG_NO_PERMISSION)
                        s.clear_query()  # 修复：清理状态，避免后续处理异常
                        return
                    self._speak_followup(s, r)
                    return

            # 没有可播号码
            self._speak(s, MSG_NO_MORE_PHONE)
            s.clear_query()
            return

        # 听不懂追问，退出 followup，重新查
        s.clear_query()
        self._handle_query(s, asr)

    def _speak_followup(self, s: Session, r: dict, notice: str = ""):
        phone = (r.get('TELE_CODE') or '').strip()
        s.followup_spoken.add(phone)
        s.followup_expires = 0.0
        cat = _phone_type_category((r.get('telephoneType') or '').strip())
        type_name = PHONE_TYPE_DISPLAY.get(cat, "")
        
        # 如果用户刚拒绝转接，话术调整
        if s.just_denied_dial:
            msg = _choose_template(MSG_NO_TRANSFER_FOLLOWUP_TEMPLATES)
            if notice:
                # 先解释，再播报号码
                msg += f"{notice}：{phone}，{phone}。"
            else:
                if type_name:
                    msg += f"他还有一个{type_name}号码是：{phone}，{phone}。"
                else:
                    msg += f"他还有一个号码是：{phone}，{phone}。"
            s.just_denied_dial = False  # 重置标志
        else:
            # 正常追问
            if notice:
                msg = f"{notice}：{phone}，{phone}。"
            else:
                if type_name:
                    msg = f"还有一个{type_name}号码是：{phone}，{phone}。"
                else:
                    msg = f"还有一个号码是：{phone}，{phone}。"
        
        msg += MSG_ASK_DIAL
        s.confirmed    = r
        s.dial_confirm = True
        s.dial_expires = time.time() + 60.0
        self._speak(s, msg, tele_code=phone)

    # ── 处理：用户直接说号码 ──────────────────
    def _handle_direct_number(self, s: Session, asr: str, phone: str):
        # 只要能走到查号码流程，说明有效对话，清零失败计数
        if s.failed_query_count > 0:
            log.info(f"反查号码，重置失败计数（之前={s.failed_query_count}）")
            s.failed_query_count = 0
            
        # 查库确认号码归属
        rec = self._lookup_phone(phone)
        if rec:
            if not self._allowed(s.caller_level, rec):
                self._speak(s, MSG_NO_PERMISSION)
                s.clear_query()
                return
            unit = rec.get('UNIT', '')
            name = rec.get('PERSONNEL', '')
            job  = rec.get('JOB', '')
            if unit == name:
                desc = f"{unit}{job}"
            else:
                desc = f"{unit}的{name}{job}"
            msg = _choose_template(
                MSG_DIRECT_NUMBER_FOUND_TEMPLATES,
                phone=phone,
                desc=desc,
                ask_dial=MSG_ASK_DIAL,
            )
        else:
            msg = _choose_template(
                MSG_DIRECT_NUMBER_NOT_FOUND_TEMPLATES,
                phone=phone,
                ask_dial=MSG_ASK_DIAL,
            )

        # 构造一个临时 result 用于转接
        fake_r = {"TELE_CODE": phone, "UNIT": unit if rec else "", "PERSONNEL": name if rec else "", "JOB": job if rec else ""}
        s.confirmed    = fake_r
        s.dial_confirm = True
        s.dial_expires = time.time() + 60.0
        self._speak(s, msg, tele_code=phone)

    # ── 处理：转人工 ──────────────────────────
    def _handle_transfer_to_human(self, s: Session):
        try:
            import core.matcher as _matcher
            if _matcher.ENABLE_MANUAL:
                s.sys_log += "用户转接人工##"
                self.handle_hangup(s.channel_id)
            else:
                s.sys_log += "用户转接人工，但是转人工功能关闭，将继续服务##"
            circuit = int(s.user_circuit) if s.user_circuit and s.user_circuit.isdigit() else s.user_circuit
            msg = f"ZRG:{s.channel_id}:{circuit:04d}"
            self.mq.publish(msg)
            log.info(f"转人工消息发送: channel={s.channel_id}")
        except Exception as e:
            log.error(f"转人工失败: {e}")

    # ── 号码追问模式初始化 ────────────────────
    def _enter_followup(self, s: Session, chosen: dict):
        person_key = (
            (chosen.get('UNIT') or '').strip(),
            (chosen.get('PERSONNEL') or '').strip(),
            (chosen.get('JOB') or '').strip(),
        )
        # 直接从数据库按 (UNIT, PERSONNEL, JOB) 找该人所有号码，不依赖查询词
        same = [
            r for r in self.matcher.phone_database
            if (
                (r.get('UNIT') or '').strip()      == person_key[0] and
                (r.get('PERSONNEL') or '').strip() == person_key[1] and
                (r.get('JOB') or '').strip()       == person_key[2]
            )
        ]
        if not same:
            same = [chosen]

        chosen_phone = (chosen.get('TELE_CODE') or '').strip()
        s.followup_person_key = person_key if same else tuple()
        s.followup_grouped    = _group_by_category(same) if same else {}
        s.followup_spoken     = {chosen_phone} if chosen_phone else set()
        s.followup_expires    = 0.0

    # ── 工具：过滤候选 ────────────────────────
    @staticmethod
    def _candidate_key(r: dict):
        return (
            (r.get('UNIT') or '').strip(),
            (r.get('PERSONNEL') or '').strip(),
            (r.get('JOB') or '').strip(),
            (r.get('TELE_CODE') or '').strip(),
        )

    def _filter_candidates_by_pinyin(self, candidates: List[dict], asr: str) -> List[dict]:
        if not asr or not candidates:
            return []
        cleaned = self._clean_hint(asr)
        user_py = self.matcher.chinese_to_pinyin(cleaned)
        user_py = self.matcher.normalize_pinyin_text(user_py, strip_tone=False)
        if not user_py:
            return []
        def expand(raw: str, fallback_text: str = "") -> List[str]:
            vs = self.matcher.expand_pinyin_variants(raw or "")
            if not vs and fallback_text:
                py = self.matcher.chinese_to_pinyin(fallback_text)
                if py:
                    vs = [py]
            return [self.matcher.normalize_pinyin_text(v, strip_tone=False) for v in vs if v]

        out = []
        for r in candidates:
            name = (r.get('PERSONNEL') or '').strip()
            unit = (r.get('UNIT') or '').strip()
            job = (r.get('JOB') or '').strip()
            abbr = (r.get('unitAbbreviation') or '').strip()
            surname = name[:1] if name else ""

            name_vs = expand(r.get('userPY', ''), name)
            sur_vs = expand(r.get('surPY', ''), surname)
            dept_vs = expand(r.get('departmentPY', ''), unit)
            job_vs = expand(r.get('jobPY', ''), job)
            abbr_vs = expand(r.get('unitAbbreviationPY', ''), abbr)

            possible = set()
            for n in name_vs:
                possible.add(n)
                for j in job_vs:
                    if j:
                        possible.add(f"{n} {j}".strip())
                for s in sur_vs:
                    for j in job_vs:
                        if j:
                            possible.add(f"{n} {s} {j}".strip())
            for d in dept_vs + abbr_vs:
                possible.add(d)
                for n in name_vs:
                    possible.add(f"{d} {n}".strip())
                    possible.add(f"{d} de5 {n}".strip())
                    for j in job_vs:
                        if j:
                            possible.add(f"{d} {n} {j}".strip())
                            possible.add(f"{d} de5 {n} {j}".strip())
                for s in sur_vs:
                    for j in job_vs:
                        if j:
                            possible.add(f"{d} {s} {j}".strip())
                            possible.add(f"{d} de5 {s} {j}".strip())
                for j in job_vs:
                    if j:
                        possible.add(f"{d} {j}".strip())
                        possible.add(f"{d} de5 {j}".strip())

            for p in possible:
                p = self.matcher.normalize_pinyin_text(p, strip_tone=False)
                if p and (p in user_py or user_py in p):
                    out.append(r)
                    break
        return out

    def _filter_candidates(self, candidates: List[dict], hint: str) -> List[dict]:
        if not hint:
            return candidates
        norm_hint = self._normalize_disambig_text(hint)
        tokens = self._extract_tokens(norm_hint)
        if not tokens:
            return []
        scored: List[tuple] = []
        for r in candidates:
            unit  = self._normalize_disambig_text((r.get('UNIT') or '').strip())
            name  = self._normalize_disambig_text((r.get('PERSONNEL') or '').strip())
            job   = self._normalize_disambig_text((r.get('JOB') or '').strip())
            abbr  = self._normalize_disambig_text((r.get('unitAbbreviation') or '').strip())
            fields = (unit, name, job, abbr)

            best = 0
            for t in tokens:
                if not t:
                    continue
                if any(t in f for f in fields if f):
                    strong = any(ch.isdigit() for ch in t) or len(t) >= 3
                    score = len(t) + (2 if strong else 0)
                    if score > best:
                        best = score
            scored.append((best, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored or scored[0][0] <= 0:
            return []
        top = scored[0][0]
        return [r for s, r in scored if s == top]

    @staticmethod
    def _clean_hint(text: str) -> str:
        stop = ["那个", "这个", "请", "麻烦", "帮我", "帮忙", "再", "一下",
                "我要", "我想", "给我", "找", "查", "转", "转接"]
        s = text.strip()
        for w in stop:
            s = s.replace(w, "")
        for c in ("的", "呢", "啊", "吧"):
            s = s.replace(c, "")
        return s.strip()

    @staticmethod
    def _normalize_disambig_text(text: str) -> str:
        if not text:
            return ""
        digit_map = {
            "零": "0", "〇": "0",
            "一": "1", "幺": "1",
            "二": "2", "两": "2",
            "三": "3", "四": "4", "五": "5",
            "六": "6", "七": "7", "八": "8", "九": "9",
        }
        out = []
        for ch in text:
            if ch in digit_map:
                out.append(digit_map[ch])
            elif ch == "第":
                continue
            else:
                out.append(ch)
        return "".join(out)

    @staticmethod
    def _extract_tokens(text: str) -> List[str]:
        parts = re.findall(r"[\u4e00-\u9fff0-9]{2,}", text)
        raw: List[str] = []
        for p in parts:
            n = len(p)
            raw.append(p)
            for size in range(2, n + 1):
                for i in range(n - size + 1):
                    raw.append(p[i:i + size])
        seen, tokens = set(), []
        for t in sorted(raw, key=len, reverse=True):
            if t not in seen:
                tokens.append(t); seen.add(t)
        return tokens

    # 意图判断统一由 IntentRouter 处理

    # ── 工具：电话类型过滤 ────────────────────
    def _apply_type_preference(self, results: List[dict], asr: str):
        keys = {(
            (r.get('UNIT') or '').strip(),
            (r.get('PERSONNEL') or '').strip(),
            (r.get('JOB') or '').strip(),
        ) for r in results}

        if len(keys) != 1:
            # 不同的人，直接返回，走多结果消歧
            return results, ""

        # 同一个人多个号码
        grouped = _group_by_category(results)
        # 用户明确类型时优先该类型
        requested_cat = _get_specific_phone_category(asr)
        if requested_cat:
            if requested_cat == "military" and any(k in asr for k in ["手机", "手机号", "移动"]):
                # 手机类优先：军用手机/军线 -> 移动电话
                for cat in ["military", "mobile"]:
                    lst = grouped.get(cat, [])
                    if lst:
                        return [lst[0]], ""
                # 没有手机类，再按默认优先级
            else:
                priority = [requested_cat] + [c for c in PHONE_TYPE_PRIORITY if c != requested_cat]
                for cat in priority:
                    lst = grouped.get(cat, [])
                    if lst:
                        return [lst[0]], ""

        # 默认优先级
        priority = ["office", "military", "mobile", "dorm", "other"]
        for cat in priority:
            lst = grouped.get(cat, [])
            if lst:
                return [lst[0]], ""

        return [results[0]], ""

    # ── 工具：查来电人信息 ────────────────────
    def _lookup_caller(self, s: Session):
        for person in self.matcher.phone_database:
            db_phone = person.get('TELE_CODE', '')
            if self._phones_match(s.caller_number, db_phone):
                s.call_name = person.get('PERSONNEL', '')
                s.call_job  = person.get('JOB', '')
                s.call_unit = person.get('UNIT', '')
                s.caller_level = self._get_level(person, default=1)
                log.info(f"来电人: {s.call_name} {s.call_job} {s.call_unit}, level={s.caller_level}")
                return
        s.caller_level = 1
        log.info(f"来电人未命中号码库，默认 level=1, caller={s.caller_number}")

    def _lookup_phone(self, phone: str) -> Optional[dict]:
        for person in self.matcher.phone_database:
            if self._phones_match(phone, person.get('TELE_CODE', '')):
                return person
        return None

    @staticmethod
    def _phones_match(p1: str, p2: str) -> bool:
        c1 = re.sub(r'\D', '', p1 or '')
        c2 = re.sub(r'\D', '', p2 or '')
        if not c1 or not c2:
            return False
        if c1 == c2:
            return True
        if len(c1) == 11 and len(c2) == 12:
            return c2[1:] == c1
        if len(c1) == 12 and len(c2) == 11:
            return c1[1:] == c2
        return False

    # ── 发言（speak）封装 ─────────────────────
    def _speak(self, s: Session, text: str, tele_code: str = "", switch_value: int = 0,
               result_unit: str = "", result_name: str = "", result_job: str = ""):
        if getattr(s, 'response_prefix', ''):
            text = s.response_prefix + text
            s.response_prefix = ""
            
        sysfilename = f"{uuid.uuid4()}.wav"
        s.sys_log     += text + "##"
        s.sys_wav_log += sysfilename + "##"
        self._send_tts(s, text, sysfilename, tele_code, switch_value,
                       result_unit, result_name, result_job)

    def _send_tts(self, s: Session, text: str, sysfilename: str,
                  tele_code: str = "", switch_value: int = 0,
                  result_unit: str = "", result_name: str = "", result_job: str = ""):
        try:
            msg = (
                f"INTE_MSG:"
                f"SEQ={s.request_id}:"
                f"TEXT={text}:"
                f"FILE={sysfilename}:"
                f"CHANNEL={s.channel_id}:"
                f"PHONE={tele_code}:"
                f"SWITCH={switch_value}:"
                f"CALLER={s.caller_number}:"
                f"CALL_NAME={s.call_name}:"
                f"CALL_JOB={s.call_job}:"
                f"CALL_UNIT={s.call_unit}:"
                f"RESULT_UNIT={result_unit}:"
                f"RESULT_NAME={result_name}:"
                f"RESULT_JOB={result_job}"
            )
            self.mq.publish(msg)
            log.info(f"TTS消息发送成功: {msg}…")

            # WebSocket 推送最后一轮对话
            user_msgs = [m for m in s.user_log.split("##") if m.strip()]
            sys_msgs  = [m for m in s.sys_log.split("##")  if m.strip()]
            if user_msgs:
                circuit = (s.user_circuit or "").zfill(4) if (s.user_circuit or "").isdigit() else s.user_circuit
                websocket_client.send_message_sync(circuit, user_msgs[-1], sys_msgs[-1] if sys_msgs else "")
        except Exception as e:
            log.error(f"发送 TTS 消息失败: {e}")

    # ── 挂断 ──────────────────────────────────
    def handle_hangup(self, channel_id: str):
        if channel_id not in self.sessions:
            return
        s = self.sessions[channel_id]
        try:
            from utils.database import insert_into_database
            insert_into_database(
                s.user_log,
                s.sys_log,
                s.wav_log,
                s.sys_wav_log,
                s.channel_id,
                s.caller_number,
                s.call_name,
                s.call_job,
                s.call_unit,
            )
            log.info(f"通道 {channel_id} 的对话数据已保存")
        except Exception as e:
            log.error(f"保存对话数据失败: {e}")
        finally:
            del self.sessions[channel_id]
            log.info(f"通道 {channel_id} 已清除")


# ──────────────────────────────────────────────
# 消息解析
# ──────────────────────────────────────────────
def parse_asr_message(msg_str: str) -> Dict[str, Any]:
    field_mapping = {
        'CHANNEL':     'channel_id',
        'SEQ':         'request_id',
        'FILE':        'filename',
        'UNIT':        'unit',
        'PERSONNEL':   'personnel_name',
        'SURNAME':     'surname',
        'POST':        'job',
        'PHONE':       'caller_number',
        'ASRCONTENT':  'asr_result',
        'USERCIRCUIT': 'user_circuit',
    }
    data: Dict[str, Any] = {}
    for item in msg_str.split(":"):
        if '=' not in item:
            continue
        key, value = item.split('=', 1)
        key   = key.strip()
        value = value.strip()
        if value.lower() in ('null', '(null)', '', 'none'):
            value = ""
        if key in field_mapping:
            data[field_mapping[key]] = value
    for mapped in field_mapping.values():
        data.setdefault(mapped, "")
    return data

def parse_hangup_message(msg_str: str) -> Optional[str]:
    for part in msg_str[len("HANGUP:"):].split(":"):
        if part.startswith("CHANNEL="):
            return part.split("=")[-1].strip()
    return None


# ──────────────────────────────────────────────
# HTTP 健康检查
# ──────────────────────────────────────────────
# 服务状态变量
service_start_time = time.time()

@app.route('/interaction/health', methods=['GET'])
def health_check():
    global service_start_time
    
    current_time = time.time()
    uptime = current_time - service_start_time if service_start_time else 0
    
    return jsonify({
        "status": "running",
        "uptime_seconds": int(uptime),
        "start_time": service_start_time,
        "current_time": current_time
    })


# ──────────────────────────────────────────────
# 主函数
# ──────────────────────────────────────────────
def main():

    load_global_configs()
    websocket_client.ensure_connection()

    manager = MainManager()

    IGNORED_PREFIXES = [
        "HEARTBEAT:ASR", "HEARTBEAT:VOICECARD", "INTE_MSG",
        "RECORD", "AI114_TTS_RESULT", "HOTWORD", "VOICECARD_START",
        "INTERACTION_START", "HEARTBEAT:PLATFORMSERVER", "ZRG", "语音卡录音程序",
    ]

    def on_message(ch, method, properties, body):
        raw = body.decode()
        if any(raw.startswith(p) for p in IGNORED_PREFIXES):
            return
        log_raw = raw
        if "FILE=" in raw:
            def _mask_file(match):
                key = match.group(1)
                val = match.group(2)
                lower = val.lower()
                if lower.endswith((".wav", ".mp3", ".pcm", ".flac", ".m4a", ".ogg")):
                    return key + val
                if len(val) > 5:
                    return key + val[:5] + "..."
                return key + val
            log_raw = re.sub(r"(FILE=)([^:]+)", _mask_file, log_raw)
        log.info(f"收到消息: {log_raw}")
        try:
            if raw.startswith("ASR_MSG:"):
                data = parse_asr_message(raw[len("ASR_MSG:"):])
                if data.get('channel_id'):
                    manager.handle(data)

            elif raw.startswith("HANGUP:"):
                cid = parse_hangup_message(raw)
                if cid:
                    manager.handle_hangup(cid)

            elif raw.startswith("UpdateAi114Config:"):
                # 运行时更新转人工/转接开关（复用 runMain.py 里的逻辑）
                for part in raw.split(":")[1:]:
                    if '=' in part:
                        k, v = part.split('=', 1)
                        import core.matcher as _matcher
                        if k.strip() == 'ai114_zrg':
                            _matcher.ENABLE_MANUAL   = (v.strip() == '1')
                        elif k.strip() == 'ai114_zj':
                            _matcher.ENABLE_TRANSFER = (v.strip() == '1')
                log.info("配置热更新完成")

        except Exception as e:
            log.error(f"处理消息异常: {e}")
            import traceback
            log.error(traceback.format_exc())

    def signal_handler(sig, frame):
        log.info("收到退出信号，关闭服务…")
        manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # HTTP 线程
    http_t = threading.Thread(
        target=lambda: app.run('0.0.0.0', 8222, use_reloader=False),
        daemon=True,
    )
    http_t.start()
    log.info("HTTP 服务已启动，监听端口 8222")

    # 发送启动通知
    mq = RabbitMQ()
    try:
        mq.publish("INTERACTION_START")
        log.info("启动通知已发送")
    except Exception as e:
        log.error(f"发送启动通知失败: {e}")

    log.info("main.py 服务启动，监听队列 AsrSend…")
    mq.consume(callback=on_message)


if __name__ == "__main__":
    main()
