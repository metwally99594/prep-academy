class CheckoutSessionRequest:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class CheckoutSession:
    def __init__(self):
        self.url = ""
        self.session_id = ""
        self.status = "open"
        self.payment_status = "unpaid"
        self.amount_total = 0
        self.currency = "eur"

class StripeCheckout:
    def __init__(self, **kwargs):
        pass
    async def create_checkout_session(self, req):
        return CheckoutSession()
    async def get_checkout_status(self, session_id):
        return CheckoutSession()
    async def handle_webhook(self, body, sig):
        return CheckoutSession()