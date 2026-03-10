import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("NEON_DATABASE_URL")

if not DATABASE_URL:
    raise EnvironmentError("❌ Variável NEON_DATABASE_URL não encontrada no .env")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("🔄 Adicionando colunas de guias físicas...")

colunas = [
    "guia_fisica_1 DATE",
    "guia_fisica_2 DATE",
    "guia_fisica_3 DATE",
    "guia_fisica_4 DATE",
    "guia_fisica_5 DATE",
]

for coluna in colunas:
    nome = coluna.split()[0]
    try:
        cursor.execute(f"ALTER TABLE datas_envio ADD COLUMN IF NOT EXISTS {coluna}")
        print(f"  ✅ Coluna {nome} adicionada")
    except Exception as e:
        print(f"  ⚠️ {nome}: {e}")

conn.commit()
cursor.close()
conn.close()
print("\n✅ Pronto! Colunas de guias físicas criadas no NeonDB.")