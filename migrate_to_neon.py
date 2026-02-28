import sqlite3
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

def migrate():
    """Migra dados do SQLite para Neon"""
    print("🔄 Iniciando migração...")
    
    # Conecta SQLite
    sqlite_conn = sqlite3.connect("prestadores.db")
    sqlite_cursor = sqlite3.connect("prestadores.db").cursor()
    
    # Conecta Neon
    neon_conn = psycopg2.connect(os.getenv("NEON_DATABASE_URL"))
    neon_cursor = neon_conn.cursor()
    
    try:
        # Migra prestadores
        sqlite_cursor.execute("SELECT * FROM prestadores")
        prestadores = sqlite_cursor.fetchall()
        
        for p in prestadores:
            neon_cursor.execute("""
                INSERT INTO prestadores (id, codigo, nome, email, data_cadastro, tipo_prestador)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (codigo) DO NOTHING
            """, p)
        
        print(f"✅ Migrados {len(prestadores)} prestadores")
        
        # Migra datas_envio
        sqlite_cursor.execute("SELECT * FROM datas_envio")
        datas = sqlite_cursor.fetchall()
        
        for d in datas:
            neon_cursor.execute("""
                INSERT INTO datas_envio 
                (id, tipo_prestador, referencia, faturamento_inicio, faturamento_fim,
                 recurso_inicio, recurso_fim, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tipo_prestador, referencia) DO NOTHING
            """, d)
        
        print(f"✅ Migrados {len(datas)} períodos")
        
        neon_conn.commit()
        print("🎉 Migração concluída com sucesso!")
        
    except Exception as e:
        neon_conn.rollback()
        print(f"❌ Erro: {e}")
    finally:
        sqlite_conn.close()
        neon_conn.close()

if __name__ == "__main__":
    migrate()