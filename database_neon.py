import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("NEON_DATABASE_URL")

if not DATABASE_URL:
    raise EnvironmentError("❌ Variável NEON_DATABASE_URL não encontrada no .env")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()

# ── Guias físicas em datas_envio ──────────────────────────────────────────────
print("🔄 Adicionando colunas de guias físicas em datas_envio...")

guias = [
    "guia_fisica_1 DATE",
    "guia_fisica_2 DATE",
    "guia_fisica_3 DATE",
    "guia_fisica_4 DATE",
    "guia_fisica_5 DATE",
]

for coluna in guias:
    nome = coluna.split()[0]
    try:
        cursor.execute(f"ALTER TABLE datas_envio ADD COLUMN IF NOT EXISTS {coluna}")
        print(f"  ✅ {nome} adicionada")
    except Exception as e:
        print(f"  ⚠️ {nome}: {e}")

# ── Coluna ativo em prestadores ───────────────────────────────────────────────
print("\n🔄 Adicionando coluna ativo em prestadores...")

try:
    cursor.execute("""
        ALTER TABLE prestadores
        ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE
    """)
    print("  ✅ ativo adicionada (prestadores existentes definidos como TRUE)")
except Exception as e:
    print(f"  ⚠️ ativo: {e}")

conn.commit()
cursor.close()
conn.close()
print("\n✅ Migração concluída!")