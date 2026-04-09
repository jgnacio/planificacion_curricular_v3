"""
Script one-shot: asigna user_id="legacy_user" a todos los rows sin user_id en ebi.db.
Correr ANTES de hacer el deploy a Supabase.

Uso:
    python scripts/migrate_add_user_id.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ebi.db")
LEGACY_USER = "legacy_user"


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] No se encontró ebi.db en {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Agregar columna user_id si no existe
    for table in ("planificaciones", "alumnos"):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT NOT NULL DEFAULT '{LEGACY_USER}'")
            print(f"[OK] Columna user_id agregada a {table}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"[SKIP] {table}.user_id ya existe")
            else:
                raise

    # Asignar legacy_user a rows que tengan user_id vacío o NULL
    for table in ("planificaciones", "alumnos"):
        cur.execute(
            f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL OR user_id = ''",
            (LEGACY_USER,),
        )
        updated = cur.rowcount
        print(f"[OK] {table}: {updated} rows actualizados a '{LEGACY_USER}'")

    conn.commit()
    conn.close()
    print("\nMigración completada. Ahora podés exportar ebi.db a Supabase.")


if __name__ == "__main__":
    migrate()
