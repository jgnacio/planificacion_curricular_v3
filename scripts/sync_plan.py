"""
Sincroniza el plan plus_mensual con Mercado Pago.
Limpia el mp_plan_id anterior (de otra cuenta) y crea uno nuevo.

Uso: .venv/bin/python3 scripts/sync_plan.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import mercadopago
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models.billing import MpPlan

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./ebi.db"
is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if is_sqlite else {})
Session = sessionmaker(bind=engine)

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
FRONT_URL = os.getenv("FRONT_URL", "https://facilitadordocente.com")

if not MP_ACCESS_TOKEN:
    print("ERROR: MP_ACCESS_TOKEN no está configurado en .env")
    sys.exit(1)

print(f"Token: {MP_ACCESS_TOKEN[:12]}...{MP_ACCESS_TOKEN[-6:]}")
print(f"Front URL: {FRONT_URL}")

import uuid
from datetime import datetime, UTC

db = Session()
plan = db.query(MpPlan).filter(MpPlan.internal_code == "plus_mensual").first()

if not plan:
    print("Plan 'plus_mensual' no existe en la DB — creándolo...")
    plan = MpPlan(
        id=str(uuid.uuid4()),
        internal_code="plus_mensual",
        display_name="Facilitador Docente PLUS",
        mp_plan_id=None,
        currency="UYU",
        unit_price_usd=400.0,
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
    plan.display_name = "Facilitador Docente PLUS"
    db.commit()

print(f"\nPlan encontrado: {plan.display_name}")
print(f"  Precio: {plan.unit_price_usd} {plan.currency}")
print(f"  Período: {plan.billing_period}")
print(f"  mp_plan_id actual: {plan.mp_plan_id or 'NINGUNO'}")

if plan.mp_plan_id:
    print(f"\nLimpiando mp_plan_id anterior ({plan.mp_plan_id})...")
    plan.mp_plan_id = None
    db.commit()
    print("Limpiado.")

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

frequency = 1 if plan.billing_period == "monthly" else 12
plan_data = {
    "reason": plan.display_name,
    "auto_recurring": {
        "frequency": frequency,
        "frequency_type": "months",
        "transaction_amount": float(plan.unit_price_usd),
        "currency_id": plan.currency,
    },
    "back_url": f"{FRONT_URL}/subscriptions/success",
    "status": "active",
}

print(f"\nCreando plan en MP con datos:")
print(f"  reason: {plan_data['reason']}")
print(f"  amount: {plan_data['auto_recurring']['transaction_amount']} {plan_data['auto_recurring']['currency_id']}")
print(f"  frequency: {frequency} months")
print(f"  back_url: {plan_data['back_url']}")

result = sdk.plan().create(plan_data)
print(f"\nStatus MP: {result['status']}")

if result["status"] not in (200, 201):
    print(f"ERROR: {result.get('response')}")
    sys.exit(1)

response = result["response"]
plan.mp_plan_id = response["id"]
db.commit()

print(f"\n✓ Plan sincronizado exitosamente")
print(f"  mp_plan_id:          {response['id']}")
print(f"  init_point:          {response.get('init_point', 'N/A')}")
print(f"  sandbox_init_point:  {response.get('sandbox_init_point', 'N/A')}")
db.close()
