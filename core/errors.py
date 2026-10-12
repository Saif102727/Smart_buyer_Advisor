"""Typed exceptions. Every error carries a *safe* Arabic message that may be shown to end users.
Technical details are only ever logged server-side, never displayed."""


class SmartBuyerError(Exception):
    user_message = "حدث خطأ غير متوقع. حاول مرة أخرى بعد قليل."

    def __init__(self, user_message: str | None = None):
        if user_message:
            self.user_message = user_message
        super().__init__(self.user_message)


class ValidationError(SmartBuyerError):
    user_message = "المدخلات غير صالحة."


class RateLimitError(SmartBuyerError):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"عدد الطلبات كبير. حاول بعد {int(retry_after) + 1} ثانية.")


class ResearchError(SmartBuyerError):
    user_message = "تعذّر إكمال البحث الآن. حاول لاحقاً."


class IntegrityError(SmartBuyerError):
    user_message = "فشل التحقق من سلامة ملف النموذج."


class AuthError(SmartBuyerError):
    user_message = "بيانات الدخول غير صحيحة."
