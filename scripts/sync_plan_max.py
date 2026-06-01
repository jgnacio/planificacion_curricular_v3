"""
Crea y sincroniza el plan Facilitador Docente MAX (800 UYU/mes) con MP.

Uso: .venv/bin/python3 scripts/sync_plan_max.py
"""
import os
import sys
import uuid
from datetime import datetime, UTC

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import mercadopago
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models.billing import MpPlan

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./ebi.db"
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
FRONT_URL = os.getenv("FRONT_URL", "https://app.facilitadordocente.com")

if not MP_ACCESS_TOKEN:
    print("ERROR: MP_ACCESS_TOKEN no configurado")
    sys.exit(1)

is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if is_sqlite else {})
Session = sessionmaker(bind=engine)

print(f"Token: {MP_ACCESS_TOKEN[:12]}...{MP_ACCESS_TOKEN[-6:]}")

db = Session()
plan = db.query(MpPlan).filter(MpPlan.internal_code == "max_mensual").first()

if not plan:
    print("Plan 'max_mensual' no existe en la DB — creándolo...")
    plan = MpPlan(
        id=str(uuid.uuid4()),
        internal_code="max_mensual",
        display_name="Facilitador Docente MAX",
        mp_plan_id=None,
        currency="UYU",
        unit_price_usd=800.0,
        billing_period="monthly",
        type="individual",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(plan)
    db.commit()
    print("Plan creado en DB.")
else:
    plan.display_name = "Facilitador Docente MAX"
    db.commit()

print(f"\nPlan: {plan.display_name}")
print(f"  Precio: {plan.unit_price_usd} {plan.currency}")
print(f"  mp_plan_id actual: {plan.mp_plan_id or 'NINGUNO'}")

if plan.mp_plan_id:
    print(f"\nLimpiando mp_plan_id anterior ({plan.mp_plan_id})...")
    plan.mp_plan_id = None
    db.commit()

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
plan_data = {
    "reason": plan.display_name,
    "auto_recurring": {
        "frequency": 1,
        "frequency_type": "months",
        "transaction_amount": float(plan.unit_price_usd),
        "currency_id": plan.currency,
    },
    "back_url": f"{FRONT_URL}/subscriptions/success",
    "status": "active",
}

print(f"\nCreando plan en MP...")
result = sdk.plan().create(plan_data)
print(f"Status MP: {result['status']}")

if result["status"] not in (200, 201):
    print(f"ERROR: {result.get('response')}")
    db.close()
    sys.exit(1)

response = result["response"]
plan.mp_plan_id = response["id"]
db.commit()

print(f"\n✓ Plan sincronizado exitosamente")
print(f"  mp_plan_id:  {response['id']}")
print(f"  init_point:  {response.get('init_point', 'N/A')}")
db.close()
