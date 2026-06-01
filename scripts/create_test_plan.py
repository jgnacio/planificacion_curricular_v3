"""
Crea un plan de prueba temporal de 50 UYU y lo sincroniza con MP.
Para eliminar después de la prueba: scripts/deactivate_test_plan.py

Uso: .venv/bin/python3 scripts/create_test_plan.py
"""
import os
import sys
import uuid

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
FRONT_URL = os.getenv("FRONT_URL", "https://app.facilitadordocente.com")

if not MP_ACCESS_TOKEN:
    print("ERROR: MP_ACCESS_TOKEN no configurado")
    sys.exit(1)

print(f"Token: {MP_ACCESS_TOKEN[:12]}...{MP_ACCESS_TOKEN[-6:]}")

db = Session()

# Verificar que no exista ya un plan de prueba
existing = db.query(MpPlan).filter(MpPlan.internal_code == "test_50_uyu").first()
if existing:
    print(f"Ya existe el plan de prueba (mp_plan_id: {existing.mp_plan_id})")
    print("Si querés recrearlo, eliminalo primero con: scripts/deactivate_test_plan.py")
    db.close()
    sys.exit(0)

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

plan_data = {
    "reason": "Plan Test 50 UYU (TEMPORAL)",
    "auto_recurring": {
        "frequency": 1,
        "frequency_type": "months",
        "transaction_amount": 50.0,
        "currency_id": "UYU",
    },
    "back_url": f"{FRONT_URL}/subscriptions/success",
    "status": "active",
}

print("\nCreando plan en MP...")
result = sdk.plan().create(plan_data)
print(f"Status MP: {result['status']}")

if result["status"] not in (200, 201):
    print(f"ERROR: {result.get('response')}")
    db.close()
    sys.exit(1)

response = result["response"]

plan = MpPlan(
    id=str(uuid.uuid4()),
    internal_code="test_50_uyu",
    display_name="Plan Test",
    mp_plan_id=response["id"],
    currency="UYU",
    unit_price_usd=50.0,
    billing_period="monthly",
    type="individual",
    is_active=True,
)
db.add(plan)
db.commit()

print(f"\n✓ Plan de prueba creado")
print(f"  internal_code: test_50_uyu")
print(f"  mp_plan_id:    {response['id']}")
print(f"  init_point:    {response.get('init_point', 'N/A')}")
print(f"\nCuando termines de probar corré: .venv/bin/python3 scripts/deactivate_test_plan.py")
db.close()
