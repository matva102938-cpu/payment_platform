from fastapi import FastAPI
from app.services.dispatcher import dispatch_order
from pydantic import BaseModel

app = FastAPI()

class MerchantOrder(BaseModel):
    id: str
    amount: int
    currency: str

@app.post("/merchant/order")
async def receive_order(order: MerchantOrder):
    success = await dispatch_order(order.dict())
    return {"status": "ok" if success else "no_trader"}
