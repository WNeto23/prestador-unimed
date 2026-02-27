# database.py
import sqlite3
from datetime import date

def init_db():
    conn = sqlite3.connect("prestadores.db")
    cursor = conn.cursor()
    
    # Tabela de Prestadores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prestadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            data_cadastro DATE DEFAULT CURRENT_DATE,
            tipo_prestador TEXT NOT NULL
        )
    ''')
    
    # Tabela de Datas de Envio
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS datas_envio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_prestador TEXT NOT NULL,
            referencia TEXT NOT NULL,
            faturamento_inicio DATE,
            faturamento_fim DATE,
            recurso_inicio DATE,
            recurso_fim DATE,
            status TEXT DEFAULT 'Ativo',
            UNIQUE(tipo_prestador, referencia)
        )
    ''')
    
    # Tabela de Log
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS log_envios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prestador_id INTEGER,
            prestador_nome TEXT,
            prestador_email TEXT,
            referencia TEXT,
            tipo_conta TEXT,
            tipo_notificacao TEXT,
            mensagem TEXT,
            data_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
            sucesso BOOLEAN DEFAULT 1,
            FOREIGN KEY (prestador_id) REFERENCES prestadores(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    return sqlite3.connect("prestadores.db")