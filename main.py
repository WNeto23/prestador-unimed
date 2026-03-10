from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

app = FastAPI(title="API Unimed RV", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_TOKEN = os.getenv("API_TOKEN", "unimed_rv_token_seguro")

def verificar_token(token: str = Header(alias="x-token")):
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    return token

def get_conn():
    return psycopg2.connect(
        os.getenv("NEON_DATABASE_URL"),
        sslmode="require",
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# ====================== STARTUP: GARANTE ESTRUTURA DO BANCO ======================
def garantir_estrutura():
    """
    Roda no startup da API.
    Usa conexão SEM RealDictCursor para comandos DDL — evita o bug silencioso
    que impedia a criação da coluna ativo na versão anterior.
    """
    conn = None
    try:
        conn = psycopg2.connect(
            os.getenv("NEON_DATABASE_URL"),
            sslmode="require"
        )
        conn.autocommit = False
        cur = conn.cursor()

        # Coluna ativo nos prestadores
        cur.execute("""
            ALTER TABLE prestadores
            ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE
        """)

        # Colunas de guias físicas em datas_envio
        for col in ["guia_fisica_1", "guia_fisica_2", "guia_fisica_3",
                    "guia_fisica_4", "guia_fisica_5"]:
            cur.execute(f"""
                ALTER TABLE datas_envio
                ADD COLUMN IF NOT EXISTS {col} DATE
            """)

        conn.commit()
        print("✅ Estrutura do banco verificada/atualizada com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao garantir estrutura do banco: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

garantir_estrutura()

# ====================== MODELS ======================
class Prestador(BaseModel):
    codigo: str
    nome: str
    email: str
    tipo_prestador: str
    ativo: bool = True

class DataEnvio(BaseModel):
    tipo_prestador: str
    referencia: str
    faturamento_inicio: Optional[str] = None
    faturamento_fim: Optional[str] = None
    recurso_inicio: Optional[str] = None
    recurso_fim: Optional[str] = None
    status: str = "Ativo"
    guia_fisica_1: Optional[str] = None
    guia_fisica_2: Optional[str] = None
    guia_fisica_3: Optional[str] = None
    guia_fisica_4: Optional[str] = None
    guia_fisica_5: Optional[str] = None

class LogEnvio(BaseModel):
    prestador_id: Optional[int] = None
    prestador_nome: str
    referencia: str
    tipo_conta: str
    tipo_notificacao: str
    sucesso: bool
    mensagem: str

# ====================== HEALTH CHECK ======================
@app.get("/")
def root():
    return {"status": "online", "sistema": "Calendário UNIMED RV"}

# ====================== PRESTADORES ======================
@app.get("/prestadores")
def listar_prestadores(token=Depends(verificar_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM prestadores ORDER BY nome")
    dados = cur.fetchall()
    conn.close()
    return list(dados)

@app.post("/prestadores")
def criar_prestador(p: Prestador, token=Depends(verificar_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO prestadores (codigo, nome, email, tipo_prestador, ativo)
        VALUES (%s, %s, %s, %s, %s) RETURNING id
    """, (p.codigo, p.nome, p.email, p.tipo_prestador, p.ativo))
    result = cur.fetchone()
    conn.commit()
    conn.close()
    return {"id": result["id"], "mensagem": "Prestador criado!"}

@app.put("/prestadores/{id}")
def atualizar_prestador(id: int, p: Prestador, token=Depends(verificar_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE prestadores
        SET codigo=%s, nome=%s, email=%s, tipo_prestador=%s, ativo=%s
        WHERE id=%s
    """, (p.codigo, p.nome, p.email, p.tipo_prestador, p.ativo, id))
    conn.commit()
    conn.close()
    return {"mensagem": "Prestador atualizado!"}

@app.delete("/prestadores/{id}")
def excluir_prestador(id: int, token=Depends(verificar_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM log_envios WHERE prestador_id = %s", (id,))
    cur.execute("DELETE FROM prestadores WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return {"mensagem": "Prestador excluído!"}

# ====================== DATAS ======================
@app.get("/datas")
def listar_datas(token=Depends(verificar_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM datas_envio ORDER BY referencia DESC")
    dados = cur.fetchall()
    conn.close()
    result = []
    for row in dados:
        r = dict(row)
        for k, v in r.items():
            if isinstance(v, date):
                r[k] = v.strftime("%Y-%m-%d")
        result.append(r)
    return result

@app.post("/datas")
def criar_data(d: DataEnvio, token=Depends(verificar_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO datas_envio 
        (tipo_prestador, referencia, faturamento_inicio, faturamento_fim,
         recurso_inicio, recurso_fim, status,
         guia_fisica_1, guia_fisica_2, guia_fisica_3, guia_fisica_4, guia_fisica_5)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """, (d.tipo_prestador, d.referencia, d.faturamento_inicio, d.faturamento_fim,
          d.recurso_inicio, d.recurso_fim, d.status,
          d.guia_fisica_1, d.guia_fisica_2, d.guia_fisica_3,
          d.guia_fisica_4, d.guia_fisica_5))
    result = cur.fetchone()
    conn.commit()
    conn.close()
    return {"id": result["id"], "mensagem": "Data criada!"}

@app.put("/datas/{id}")
def atualizar_data(id: int, d: DataEnvio, token=Depends(verificar_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE datas_envio SET
            tipo_prestador=%s, referencia=%s,
            faturamento_inicio=%s, faturamento_fim=%s,
            recurso_inicio=%s, recurso_fim=%s, status=%s,
            guia_fisica_1=%s, guia_fisica_2=%s,
            guia_fisica_3=%s, guia_fisica_4=%s, guia_fisica_5=%s
        WHERE id=%s
    """, (d.tipo_prestador, d.referencia, d.faturamento_inicio, d.faturamento_fim,
          d.recurso_inicio, d.recurso_fim, d.status,
          d.guia_fisica_1, d.guia_fisica_2, d.guia_fisica_3,
          d.guia_fisica_4, d.guia_fisica_5, id))
    conn.commit()
    conn.close()
    return {"mensagem": "Data atualizada!"}

@app.delete("/datas/{id}")
def excluir_data(id: int, token=Depends(verificar_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM datas_envio WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return {"mensagem": "Data excluída!"}

# ====================== LOG ======================
@app.get("/log")
def listar_log(token=Depends(verificar_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM log_envios ORDER BY data_envio DESC LIMIT 200")
    dados = cur.fetchall()
    conn.close()
    result = []
    for row in dados:
        r = dict(row)
        for k, v in r.items():
            if hasattr(v, 'isoformat'):
                r[k] = v.isoformat()
        result.append(r)
    return result

@app.post("/log")
def registrar_log(l: LogEnvio, token=Depends(verificar_token)):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO log_envios 
        (prestador_id, prestador_nome, referencia, tipo_conta,
         tipo_notificacao, sucesso, mensagem)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (l.prestador_id, l.prestador_nome, l.referencia,
          l.tipo_conta, l.tipo_notificacao, l.sucesso, l.mensagem))
    conn.commit()
    conn.close()
    return {"mensagem": "Log registrado!"}