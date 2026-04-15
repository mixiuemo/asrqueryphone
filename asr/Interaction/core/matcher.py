import json
import re
from typing import List, Dict, Optional

from pypinyin import pinyin, Style

from utils.loggeruitls import Logger
from core.config import PHONE_TYPE_KEYWORDS


log = Logger()


class PhoneTypeExtractor:
    def __init__(self):
        self.type_mapping = PHONE_TYPE_KEYWORDS

    def extract_type(self, asr_result: str) -> str:
        for phone_type, aliases in self.type_mapping.items():
            for alias in aliases:
                if asr_result == alias:
                    return phone_type
                if alias in asr_result:
                    if alias == "手机" and phone_type == "军用手机":
                        return "军用手机"
                    if phone_type == "军用手机" and alias != "手机" and "军用" not in asr_result and "军线" not in asr_result:
                        continue
                    return phone_type
        return ""

    def normalize_department(self, dept: str) -> str:
        for std, aliases in self.type_mapping.items():
            for alias in aliases:
                if alias in dept:
                    return std
        return dept


class PinyinMatcher:
    DIGIT_TO_CN = str.maketrans({
        "0": "零",
        "1": "一",
        "2": "二",
        "3": "三",
        "4": "四",
        "5": "五",
        "6": "六",
        "7": "七",
        "8": "八",
        "9": "九",
    })

    def __init__(self):
        self.phone_database = self._load_phone_database()
        self.query_templates = self._load_query_templates()
        self.query_templates_no_tone = self._load_query_templates("./data/query_templates_no_tone.json")
        self.template_set = set(self.query_templates)
        self.template_set_no_tone = set(self.query_templates_no_tone)
        self._template_index, self._template_max_len = self._build_template_index(self.template_set)
        self._template_index_no_tone, self._template_max_len_no_tone = self._build_template_index(
            self.template_set_no_tone
        )
        self.unit_lexicon, self.unit_lexicon_norm, self.unit_lexicon_pinyin = self._build_unit_lexicon()

    def rebuild_unit_lexicon(self):
        self.unit_lexicon, self.unit_lexicon_norm, self.unit_lexicon_pinyin = self._build_unit_lexicon()

    def _load_phone_database(self, file_path: str = "./data/phone_database.json"):
        try:
            for enc in ["utf-8", "gbk", "gb2312", "utf-8-sig"]:
                try:
                    with open(file_path, "r", encoding=enc) as f:
                        data = json.load(f)
                        if data:
                            return data
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
            log.error("无法读取 phone_database.json 文件")
            return []
        except (FileNotFoundError, json.JSONDecodeError) as e:
            log.error(f"加载 phone_database.json 失败: {e}")
            return []

    def _load_query_templates(self, file_path: str = "./data/query_templates.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data:
                return []
            clean = []
            for t in data:
                inner = re.findall(r"\{([^{}]+)\}", t)
                if inner:
                    clean.append(" ".join(inner))
            return clean
        except (FileNotFoundError, json.JSONDecodeError) as e:
            log.error(f"加载 query_templates.json 失败: {e}")
            return []

    @staticmethod
    def chinese_to_pinyin(text: str) -> str:
        if not text:
            return ""
        normalized_text = text.translate(PinyinMatcher.DIGIT_TO_CN)
        py = pinyin(normalized_text, style=Style.TONE3, heteronym=False)
        tokens = [item[0] for item in py]
        # pypinyin returns "de" for "的"; templates use "de5".
        tokens = ["de5" if t == "de" else t for t in tokens]
        return " ".join(tokens)

    @staticmethod
    def _cn_num_to_int(s: str):
        if not s:
            return None
        digits = {
            "零": 0, "〇": 0,
            "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
            "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
        }
        if "十" in s:
            parts = s.split("十", 1)
            tens = parts[0]
            ones = parts[1]
            tens_val = 1 if tens == "" else digits.get(tens, None)
            ones_val = 0 if ones == "" else digits.get(ones, None)
            if tens_val is None or ones_val is None:
                return None
            return tens_val * 10 + ones_val
        if len(s) == 1 and s in digits:
            return digits[s]
        return None

    def _normalize_digits_for_disambiguation(self, text: str) -> str:
        if not text:
            return ""
        # 全角数字 -> 半角
        fullwidth_digits = str.maketrans("０１２３４５６７８９", "0123456789")
        normalized = text.translate(fullwidth_digits)

        # 先处理含“十”的中文数（0-99）
        def _cn_ten_repl(m: re.Match) -> str:
            val = self._cn_num_to_int(m.group(0))
            return str(val) if val is not None else m.group(0)

        normalized = re.sub(r"[一二两三四五六七八九]?十[一二三四五六七八九]?", _cn_ten_repl, normalized)

        # 常见中文数字字符 -> 阿拉伯数字（逐字）
        cn_to_digit = {
            "零": "0", "〇": "0", "○": "0",
            "一": "1", "壹": "1", "幺": "1",
            "二": "2", "贰": "2", "两": "2",
            "三": "3", "叁": "3",
            "四": "4", "肆": "4",
            "五": "5", "伍": "5",
            "六": "6",
            "七": "7", "柒": "7",
            "八": "8", "捌": "8",
            "九": "9", "玖": "9",
        }
        normalized = "".join(cn_to_digit.get(ch, ch) for ch in normalized)
        return normalized

    def _build_unit_lexicon(self):
        units = []
        for r in self.phone_database or []:
            unit = (r.get("UNIT") or "").strip()
            abbr = (r.get("unitAbbreviation") or "").strip()
            for u in (unit, abbr):
                if not u:
                    continue
                if len(u) >= 2 or any(ch.isdigit() for ch in u):
                    units.append(u)
        units = sorted(set(units), key=len, reverse=True)
        unit_norm = [self._normalize_digits_for_disambiguation(u) for u in units]
        unit_pinyin = [self.chinese_to_pinyin(u) for u in units]
        return units, unit_norm, unit_pinyin

    def extract_unit_hints(self, text: str):
        if not text:
            return []
        if not self.unit_lexicon:
            return []
        norm_text = self._normalize_digits_for_disambiguation(text)
        hits = []
        for u_norm in self.unit_lexicon_norm or []:
            if u_norm and u_norm in norm_text:
                hits.append(u_norm)
        if not hits:
            text_py = self.chinese_to_pinyin(text)
            for u_norm, u_py in zip(self.unit_lexicon_norm or [], self.unit_lexicon_pinyin or []):
                if u_py and u_py in text_py:
                    hits.append(u_norm)
        if not hits:
            return []
        hits = sorted(set(hits), key=len, reverse=True)
        max_len = len(hits[0])
        return [h for h in hits if len(h) == max_len]

    def filter_results_by_unit_hint(self, results: List[Dict], text: str) -> List[Dict]:
        if not results:
            return results
        hints = self.extract_unit_hints(text)
        if not hints:
            return results
        filtered = []
        for r in results:
            unit = (r.get("UNIT") or "").strip()
            abbr = (r.get("unitAbbreviation") or "").strip()
            unit_norm = self._normalize_digits_for_disambiguation(unit)
            abbr_norm = self._normalize_digits_for_disambiguation(abbr)
            # # 单位信息为空时不参与过滤，避免把“纠察”等无单位记录误过滤
            # if not unit_norm and not abbr_norm:
            #     filtered.append(r)
            #     continue
            if any(h in unit_norm or (abbr_norm and h in abbr_norm) for h in hints):
                filtered.append(r)
        return filtered

    def _get_role_class_tokens(self, text: str):
        if not text:
            return []
        role_class = ["一号台", "二号台", "长途台", "综合台", "查号台", "总机", "1号台", "2号台"]
        hits = []
        for r in role_class:
            if r in text:
                hits.append(r)
        return hits

    def _get_role_label_for_record(self, record: Dict) -> str:
        role_priority = ["总机", "查号台", "综合台", "长途台", "二号台", "一号台"]
        name = (record.get("PERSONNEL") or "").strip()
        job = (record.get("JOB") or "").strip()
        combined = f"{name}{job}"
        for role in role_priority:
            if role in combined:
                return role
        if "1号台" in combined:
            return "一号台"
        if "2号台" in combined:
            return "二号台"
        return ""

    def fallback_role_class_by_unit(self, text: str):
        role_tokens = self._get_role_class_tokens(text)
        if not role_tokens:
            return None
        unit_hints = self.extract_unit_hints(text)
        if not unit_hints:
            return None
        role_priority = ["总机", "查号台", "综合台", "长途台", "二号台", "一号台"]
        candidates = []
        for r in self.phone_database or []:
            unit = (r.get("UNIT") or "").strip()
            abbr = (r.get("unitAbbreviation") or "").strip()
            unit_norm = self._normalize_digits_for_disambiguation(unit)
            abbr_norm = self._normalize_digits_for_disambiguation(abbr)
            if not any(h == unit_norm or (abbr_norm and h == abbr_norm) for h in unit_hints):
                continue
            role_label = self._get_role_label_for_record(r)
            if role_label in role_priority:
                candidates.append((r, role_label))
        if not candidates:
            return None
        def _rank(label: str) -> int:
            try:
                return role_priority.index(label)
            except ValueError:
                return 999
        candidates.sort(key=lambda x: _rank(x[1]))
        chosen, role_label = candidates[0]
        unit_display = (chosen.get("UNIT") or "").strip() or (chosen.get("unitAbbreviation") or "").strip()
        return unit_display, role_label, [chosen]

    @staticmethod
    def normalize_pinyin_text(text: str, *, strip_tone: bool = True) -> str:
        if not text:
            return ""
        tokens = re.split(r"\s+", str(text).strip().lower())
        normalized = []
        for token in tokens:
            if not token:
                continue
            if strip_tone:
                # Remove tone digits only when they are pinyin tone marks (e.g. "yang2"),
                # while preserving numeric identifiers like "84".
                token = re.sub(r"(?<=[a-z])[1-5]$", "", token)
            normalized.append(token)
        return " ".join(normalized)

    @staticmethod
    def _build_template_index(templates: set):
        by_len = {}
        max_len = 0
        for t in templates or []:
            tokens = [x for x in str(t).split() if x]
            if not tokens:
                continue
            tlen = len(tokens)
            if tlen > max_len:
                max_len = tlen
            bucket = by_len.setdefault(tlen, set())
            bucket.add(" ".join(tokens))
        return by_len, max_len

    def find_longest_match(
        self,
        user_text: str,
        *,
        template_set: Optional[set] = None,
        strip_tone: bool = False,
        log_tag: str = "",
    ) -> str:
        cleaned_text = self.clean_text(user_text)
        user_py = self.chinese_to_pinyin(cleaned_text)
        tag = f"[{log_tag}] " if log_tag else ""
        log.info(f"{tag}输入: {user_text}, 清洗: {cleaned_text}, 转换拼音: {user_py}")

        if strip_tone:
            user_py = self.normalize_pinyin_text(user_py, strip_tone=True)
        tokens = [t for t in (user_py or "").split() if t]
        template_set = template_set or self.template_set
        if not tokens or not template_set:
            return ""

        if template_set is self.template_set:
            template_index = self._template_index
            max_len = self._template_max_len
        elif template_set is self.template_set_no_tone:
            template_index = self._template_index_no_tone
            max_len = self._template_max_len_no_tone
        else:
            template_index, max_len = self._build_template_index(template_set)

        if not template_index or max_len <= 0:
            return ""

        n = len(tokens)
        max_len = min(max_len, n)
        for length in range(max_len, 0, -1):
            bucket = template_index.get(length)
            if not bucket:
                continue
            for i in range(0, n - length + 1):
                cand = " ".join(tokens[i : i + length])
                if cand in bucket:
                    return cand
        return ""

    @staticmethod
    def expand_pinyin_variants(pinyin_str: str):
        if not pinyin_str:
            return []
        variants = sorted(set(v.strip() for v in pinyin_str.split("|")), key=len, reverse=True)
        return [v for v in variants if v]

    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        stop_words = [
            "找一下",
            "查一下",
            "给我接",
            "转接",
            "帮我找",
            "帮我查",
            "我想找",
            "请问有",
            "有没有",
            "转一下",
            "是多少",
            "号码是多少",
            "找下",
            "一下",
            "那个",
            "那个啥",
            "啥来着",
            "我想一下",
            "我想一想",
            "想一下",
            "请帮我",
            "给我",
            "搜一下",
            "查询",
            "啊",
            "吧",
            "呢",
            "嗯",
            "呃",
        ]

        cleaned_text = text
        for word in stop_words:
            cleaned_text = cleaned_text.replace(word, "")

        return cleaned_text

    def find_matches(self, user_input: str) -> List[Dict]:
        if not self.phone_database or not self.query_templates:
            log.error("电话数据库或查询模板未加载")
            return []

        log.info(f"开始拼音匹配查询: {user_input}")
        matched_template = self.find_longest_match(user_input, log_tag="tone")
        use_no_tone = False

        if not matched_template and self.template_set_no_tone:
            matched_template = self.find_longest_match(
                user_input,
                template_set=self.template_set_no_tone,
                strip_tone=True,
                log_tag="no_tone",
            )
            if matched_template:
                use_no_tone = True
                log.info("无音调模板兜底命中")

        if not matched_template:
            log.info("没有找到匹配的模板")
            return []

        log.info(f"匹配到模板: {matched_template}")
        matched_template_normalized = self.normalize_pinyin_text(matched_template, strip_tone=use_no_tone)

        results = []
        seen_people = set()

        for person in self.phone_database:
            name = person.get("PERSONNEL", "")
            department = person.get("UNIT", "")
            position = person.get("JOB", "")

            def _pick_variants(key_tone: str, key_no_tone: str):
                val = person.get(key_no_tone if use_no_tone else key_tone, "")
                if not val and use_no_tone:
                    tone_val = person.get(key_tone, "")
                    if tone_val:
                        val = self.normalize_pinyin_text(tone_val, strip_tone=True)
                return self.expand_pinyin_variants(val)

            name_py_variants = _pick_variants("userPY", "userPY_no_tone")
            dept_py_variants = _pick_variants("departmentPY", "departmentPY_no_tone")
            job_py_variants = _pick_variants("jobPY", "jobPY_no_tone")
            unit_abbr_py_variants = _pick_variants("unitAbbreviationPY", "unitAbbreviationPY_no_tone")
            surname_py_variants = _pick_variants("surPY", "surPY_no_tone")

            if not name_py_variants and name:
                name_py = self.chinese_to_pinyin(name)
                name_py_variants = [self.normalize_pinyin_text(name_py, strip_tone=use_no_tone)]
            if not dept_py_variants and department:
                dept_py = self.chinese_to_pinyin(department)
                dept_py_variants = [self.normalize_pinyin_text(dept_py, strip_tone=use_no_tone)]
            if not dept_py_variants:
                dept_py_variants = [""]
            if not job_py_variants and position:
                job_py = self.chinese_to_pinyin(position)
                job_py_variants = [self.normalize_pinyin_text(job_py, strip_tone=use_no_tone)]
            if not job_py_variants:
                job_py_variants = [""]
            if not unit_abbr_py_variants and person.get("unitAbbreviation"):
                abbr_py = self.chinese_to_pinyin(person.get("unitAbbreviation", ""))
                unit_abbr_py_variants = [self.normalize_pinyin_text(abbr_py, strip_tone=use_no_tone)]
            if not surname_py_variants and name:
                sur_py = self.chinese_to_pinyin(name[0])
                surname_py_variants = [self.normalize_pinyin_text(sur_py, strip_tone=use_no_tone)]

            matched = False
            de_token = "de" if use_no_tone else "de5"
            for name_py in name_py_variants:
                for dept_py in dept_py_variants:
                    for job_py in job_py_variants:
                        possible_matches = [
                            f"{dept_py} {name_py} {job_py}",
                            f"{dept_py} {name_py}",
                            f"{dept_py} {job_py}",
                            f"{name_py} {job_py}",
                            f"{name_py}",
                            f"{dept_py} {de_token} {name_py} {job_py}",
                            f"{dept_py} {de_token} {name_py}",
                            f"{dept_py} {de_token} {job_py}",
                        ]

                        for surname_py in surname_py_variants:
                            possible_matches.extend(
                                [
                                    f"{dept_py} {surname_py} {job_py}",
                                    f"{name_py} {surname_py} {job_py}",
                                    f"{surname_py} {job_py}",
                                    f"{dept_py} {de_token} {surname_py} {job_py}",
                                ]
                            )

                        for unit_abbr_py in unit_abbr_py_variants:
                            possible_matches.extend(
                                [
                                    f"{unit_abbr_py} {name_py} {job_py}",
                                    f"{unit_abbr_py} {name_py}",
                                    f"{name_py} {unit_abbr_py} {job_py}",
                                    f"{unit_abbr_py} {job_py}",
                                    unit_abbr_py,
                                    f"{unit_abbr_py} {de_token} {name_py} {job_py}",
                                    f"{unit_abbr_py} {de_token} {name_py}",
                                    f"{unit_abbr_py} {de_token} {job_py}",
                                ]
                            )
                            for surname_py in surname_py_variants:
                                possible_matches.extend(
                                    [
                                        f"{unit_abbr_py} {surname_py} {job_py}",
                                        f"{unit_abbr_py} {de_token} {surname_py} {job_py}",
                                    ]
                                )

                        for possible_match in possible_matches:
                            normalized_possible_match = self.normalize_pinyin_text(
                                possible_match.strip(), strip_tone=use_no_tone
                            )
                            if normalized_possible_match == matched_template_normalized:
                                matched = True
                                log.info(f"匹配成功: {possible_match} == {matched_template}")
                                break
                        if matched:
                            break
                    if matched:
                        break
                if matched:
                    phone = person.get("TELE_CODE", "")
                    normalized_name = re.sub(r"\s+", "", str(name or ""))
                    normalized_phone = re.sub(r"\s+", "", str(phone or ""))
                    normalized_department = re.sub(r"\s+", "", str(department or ""))
                    person_key = f"{normalized_name}_{normalized_phone}_{normalized_department}"
                    if person_key not in seen_people:
                        results.append(person)
                        seen_people.add(person_key)
                        log.info(f"找到匹配: {matched_template} -> {name}")
                    break

        log.info(f"拼音匹配查询完成，找到 {len(results)} 个匹配结果")
        return results


def load_global_configs():
    global ENABLE_TRANSFER, ENABLE_MANUAL
    ENABLE_TRANSFER = True
    ENABLE_MANUAL = True
    try:
        from utils.database import load_system_config
        ENABLE_TRANSFER, ENABLE_MANUAL = load_system_config()
        log.info(f"从数据库加载配置: 自动转接功能状态={ENABLE_TRANSFER}, 转人工状态={ENABLE_MANUAL}")
    except Exception as e:
        log.error(f"加载配置失败，使用默认配置: {e}")
        log.info(f"全局配置初始化: 自动转接功能状态={ENABLE_TRANSFER}, 转人工状态={ENABLE_MANUAL}")
