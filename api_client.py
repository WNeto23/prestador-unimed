"""
api_client.py - Cliente da API Unimed RV
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL   = os.getenv("API_URL",   "https://web-production-80dc.up.railway.app")
API_TOKEN = os.getenv("API_TOKEN", "unimed_rv_2026_token_seguro")
HEADERS   = {"x-token": API_TOKEN}

def api_get(endpoint):
    r = requests.get(f"{API_URL}{endpoint}", headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()

def api_post(endpoint, data):
    r = requests.post(f"{API_URL}{endpoint}", json=data, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()

def api_put(endpoint, data):
    r = requests.put(f"{API_URL}{endpoint}", json=data, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()

def api_delete(endpoint):
    r = requests.delete(f"{API_URL}{endpoint}", headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()

# ====================== PRESTADORES ======================
def listar_prestadores(filtro=""):
    dados = api_get("/prestadores")
    if filtro:
        f = filtro.lower()
        dados = [d for d in dados if
                 f in d.get("codigo","").lower() or
                 f in d.get("nome","").lower() or
                 f in d.get("email","").lower()]
    return [(d["id"], d["codigo"], d["nome"], d["email"],
             d["tipo_prestador"], d.get("data_cadastro",""),
             d.get("ativo", True)) for d in dados]

def criar_prestador(codigo, nome, email, tipo_prestador, ativo=True):
    return api_post("/prestadores", {
        "codigo": codigo, "nome": nome,
        "email": email, "tipo_prestador": tipo_prestador,
        "ativo": ativo
    })

def atualizar_prestador(id, codigo, nome, email, tipo_prestador, ativo=True):
    return api_put(f"/prestadores/{id}", {
        "codigo": codigo, "nome": nome,
        "email": email, "tipo_prestador": tipo_prestador,
        "ativo": ativo
    })

def excluir_prestador(id):
    return api_delete(f"/prestadores/{id}")

def buscar_prestador(id):
    for d in api_get("/prestadores"):
        if d["id"] == id:
            return d
    return None

# ====================== DATAS ======================
def listar_datas_envio(filtro=""):
    dados = api_get("/datas")
    if filtro:
        f = filtro.lower()
        dados = [d for d in dados if
                 f in d.get("tipo_prestador","").lower() or
                 f in d.get("referencia","").lower()]
    return [(d["id"], d["tipo_prestador"], d["referencia"],
             d.get("faturamento_inicio"), d.get("faturamento_fim"),
             d.get("recurso_inicio"), d.get("recurso_fim"),
             d.get("status","Ativo"),
             d.get("guia_fisica_1"), d.get("guia_fisica_2"), d.get("guia_fisica_3"),
             d.get("guia_fisica_4"), d.get("guia_fisica_5")) for d in dados]

def criar_data(tipo_prestador, referencia, fat_ini, fat_fim,
               rec_ini, rec_fim, status,
               g1=None, g2=None, g3=None, g4=None, g5=None):
    return api_post("/datas", {
        "tipo_prestador": tipo_prestador, "referencia": referencia,
        "faturamento_inicio": fat_ini, "faturamento_fim": fat_fim,
        "recurso_inicio": rec_ini, "recurso_fim": rec_fim, "status": status,
        "guia_fisica_1": g1, "guia_fisica_2": g2, "guia_fisica_3": g3,
        "guia_fisica_4": g4, "guia_fisica_5": g5
    })

def atualizar_data(id, tipo_prestador, referencia, fat_ini, fat_fim,
                   rec_ini, rec_fim, status,
                   g1=None, g2=None, g3=None, g4=None, g5=None):
    return api_put(f"/datas/{id}", {
        "tipo_prestador": tipo_prestador, "referencia": referencia,
        "faturamento_inicio": fat_ini, "faturamento_fim": fat_fim,
        "recurso_inicio": rec_ini, "recurso_fim": rec_fim, "status": status,
        "guia_fisica_1": g1, "guia_fisica_2": g2, "guia_fisica_3": g3,
        "guia_fisica_4": g4, "guia_fisica_5": g5
    })

def excluir_data(id):
    return api_delete(f"/datas/{id}")

def buscar_data(id):
    for d in api_get("/datas"):
        if d["id"] == id:
            return d
    return None

# ====================== LOG ======================
def listar_log_envios(limite=100):
    dados = api_get("/log")[:limite]
    return [(d.get("data_envio"), d.get("prestador_nome"),
             d.get("referencia"), d.get("tipo_conta"),
             d.get("tipo_notificacao"), 1 if d.get("sucesso") else 0)
            for d in dados]

def registrar_log(prestador_id, prestador_nome, referencia,
                  tipo_conta, tipo_notificacao, sucesso, mensagem):
    return api_post("/log", {
        "prestador_id": prestador_id, "prestador_nome": prestador_nome,
        "referencia": referencia, "tipo_conta": tipo_conta,
        "tipo_notificacao": tipo_notificacao,
        "sucesso": bool(sucesso), "mensagem": mensagem
    })

# ====================== MÉTRICAS ======================
def contar_prestadores():
    # Conta apenas ativos
    return sum(1 for d in api_get("/prestadores") if d.get("ativo", True))

def contar_datas_ativas():
    return sum(1 for d in api_get("/datas") if d.get("status") == "Ativo")

def contar_falhas_7dias():
    from datetime import datetime, timedelta
    logs = api_get("/log")
    sete_dias = datetime.now() - timedelta(days=7)
    return sum(1 for l in logs
               if not l.get("sucesso") and l.get("data_envio") and
               datetime.fromisoformat(l["data_envio"][:19]) >= sete_dias)