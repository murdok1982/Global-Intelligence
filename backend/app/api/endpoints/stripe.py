import stripe
from fastapi import APIRouter, Header, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.session import AsyncSessionLocal

stripe.api_key = settings.STRIPE_SECRET_KEY
router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "customer.subscription.created":
        subscription = event["data"]["object"]
        # Hook into Subscriptions schema here
    elif event["type"] == "customer.subscription.updated":
        pass
    elif event["type"] == "customer.subscription.deleted":
        pass
        
    return {"status": "success"}

@router.post("/create-checkout-session")
async def create_checkout_session(plan_type: str):
    price_id = "price_id_placeholder_100_eur" if plan_type == 'individual' else "price_id_placeholder_10000_eur"
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{ 'price': price_id, 'quantity': 1 }],
            mode='subscription',
            success_url="http://localhost:3000/dashboard?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="http://localhost:3000/pricing?cancelled=true",
        )
        return {"id": checkout_session.id, "url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
