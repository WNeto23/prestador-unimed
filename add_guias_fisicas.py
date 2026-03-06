from database_neon import neon_db

conn = neon_db.get_connection()
cursor = conn.cursor()

print("🔄 Adicionando colunas de guias físicas...")

colunas = [
    "guia_fisica_1 DATE",
    "guia_fisica_2 DATE",
    "guia_fisica_3 DATE",
    "guia_fisica_4 DATE",
]

for coluna in colunas:
    nome = coluna.split()[0]
    try:
        cursor.execute(f"ALTER TABLE datas_envio ADD COLUMN IF NOT EXISTS {coluna}")
        print(f"  ✅ Coluna {nome} adicionada")
    except Exception as e:
        print(f"  ⚠️ {nome}: {e}")

conn.commit()
neon_db.return_connection(conn)
print("\n✅ Pronto! Colunas de guias físicas criadas no NeonDB.")