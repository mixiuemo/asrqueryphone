class PhoneLocation:
    # Lengths that can be treated as direct dial numbers from ASR.
    DIRECT_DIAL_LENGTHS = (4, 6, 11)

    @staticmethod
    def _digits_only(phone_number: str) -> str:
        return "".join(ch for ch in str(phone_number or "") if ch.isdigit())

    @staticmethod
    def get_prefix_code(phone_number: str) -> str:
        digits = PhoneLocation._digits_only(phone_number)
        # 4-digit and 6-digit numbers do not use transfer prefix.
        if len(digits) in (4, 6):
            return ""
        # Only 11-digit mobile numbers use prefix routing rules.
        # Landlines with area codes (e.g. 021xxxxxxx) should not be prefixed.
        if len(digits) != 11:
            return ""
        if digits.startswith("1"):
            return "20"
        return ""

    @staticmethod
    def format_dial_number(phone_number: str) -> str:
        """
        Standardize number used for real transfer dialing.
        Rules:
        - 4 and 6 digits: no prefix
        - 11-digit mobile (starts with "1"): prefix "20"
        - other lengths: keep original value (including landlines with area codes)
        """
        raw = (phone_number or "").strip()
        digits = PhoneLocation._digits_only(raw)
        prefix = PhoneLocation.get_prefix_code(digits)
        if not prefix:
            return raw
        return prefix + digits
