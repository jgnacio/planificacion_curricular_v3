"""
Seed de los 4 planes individuales (básico/MAX × mensual/anual) en mp_plans.

Solo inserta filas locales — NO sincroniza con Mercado Pago. La sincronización
se hace después, por plan, vía POST /admin/plans/{id}/sync (ver
api/routes/subscriptions.py:sync_plan_to_mp).

Internal codes EXACTOS — access_control.MAX_PLAN_CODES depende de
"max_mensual" y "max_anual" tal cual.

Uso: uv run python scripts/seed_plans.py
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models.billing import MpPlan

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./ebi.db"
is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if is_sqlite else {})
Session = sessionmaker(bind=engine)

CURRENCY = "UYU"
BASICO_MENSUAL_PRICE = 10.0  # placeholder ~400 UYU
MAX_MENSUAL_PRICE = 20.0     # placeholder ~800 UYU

PLANS = [
    {
        "internal_code": "basico_mensual",
        "display_name": "Facilitador Docente Básico — Mensual",
        "unit_price_usd": BASICO_MENSUAL_PRICE,
        "billing_period": "monthly",
    },
    {
        "internal_code": "basico_anual",
        "display_name": "Facilitador Docente Básico — Anual",
        "unit_price_usd": BASICO_MENSUAL_PRICE * 10,  # precio de 10 meses
        "billing_period": "annual",
    },
    {
        "internal_code": "max_mensual",
        "display_name": "Facilitador Docente MAX — Mensual",
        "unit_price_usd": MAX_MENSUAL_PRICE,
        "billing_period": "monthly",
    },
    {
        "internal_code": "max_anual",
        "display_name": "Facilitador Docente MAX — Anual",
        "unit_price_usd": MAX_MENSUAL_PRICE * 10,  # precio de 10 meses
        "billing_period": "annual",
    },
]


def main() -> None:
    db = Session()
    try:
        for spec in PLANS:
            existing = db.query(MpPlan).filter(
                MpPlan.internal_code == spec["internal_code"]
            ).first()
            if existing:
                print(f"  = {spec['internal_code']} ya existe (mp_plan_id: {existing.mp_plan_id}) — omitido")
                continue

            plan = MpPlan(
                id=str(uuid.uuid4()),
                internal_code=spec["internal_code"],
                display_name=spec["display_name"],
                mp_plan_id=None,
                currency=CURRENCY,
                unit_price_usd=spec["unit_price_usd"],
                billing_period=spec["billing_period"],
                type="individual",
                is_active=True,
            )
            db.add(plan)
            print(f"  + {spec['internal_code']} creado (sin sync a MP todavía)")

        db.commit()
        print("\nListo. Sincronizar cada plan con MP vía POST /admin/plans/{id}/sync antes de aceptar checkouts.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
