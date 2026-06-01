"""
Desactiva el plan de prueba temporal en MP y en la DB.

Uso: .venv/bin/python3 scripts/deactivate_test_plan.py
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
if not MP_ACCESS_TOKEN:
    print("ERROR: MP_ACCESS_TOKEN no configurado")
    sys.exit(1)

db = Session()
plan = db.query(MpPlan).filter(MpPlan.internal_code == "test_50_uyu").first()

if not plan:
    print("No se encontró el plan de prueba (test_50_uyu) en la DB")
    db.close()
    sys.exit(0)

print(f"Plan encontrado: {plan.display_name} (mp_plan_id: {plan.mp_plan_id})")

if plan.mp_plan_id:
    sdk = mercadopago.SDK(MP_ACCESS_TOKEN)
    result = sdk.plan().update(plan.mp_plan_id, {"status": "inactive"})
    if result["status"] in (200, 201):
        print("✓ Plan desactivado en MP")
    else:
        print(f"Advertencia MP: {result.get('response')}")

plan.is_active = False
db.commit()
print("✓ Plan desactivado en DB")
print("\nListo — el plan de prueba ya no aparece para nuevos usuarios.")
db.close()
