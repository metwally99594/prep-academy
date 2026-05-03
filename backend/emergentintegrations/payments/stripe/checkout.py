class StripeCheckout:
    def __init__(self, **kwargs):
        pass
    async def create_session(self, **kwargs):
        return {"url": "", "session_id": ""}
    async def verify_payment(self, **kwargs):
        return False