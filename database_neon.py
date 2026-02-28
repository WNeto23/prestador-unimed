import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class NeonDatabase:
    """Gerenciador de conexão com NeonDB (PostgreSQL)"""
    
    _instance = None
    _connection_pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self):
        """Inicializa o pool de conexões"""
        try:
            database_url = os.getenv("NEON_DATABASE_URL")
            if not database_url:
                logger.warning("NEON_DATABASE_URL não configurado, usando SQLite")
                return
            
            # Pool de conexões (mínimo 1, máximo 10)
            self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                dsn=database_url,
                sslmode='require'
            )
            logger.info("✅ Pool de conexões NeonDB inicializado")
            
            # Cria tabelas se não existirem
            self._create_tables()
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao NeonDB: {e}")
            self._connection_pool = None
    
    def _create_tables(self):
        """Cria as tabelas no PostgreSQL"""
        with self.get_cursor() as cursor:
            # Tabela de prestadores
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prestadores (
                    id SERIAL PRIMARY KEY,
                    codigo VARCHAR(50) UNIQUE NOT NULL,
                    nome VARCHAR(200) NOT NULL,
                    email VARCHAR(200) NOT NULL,
                    data_cadastro DATE DEFAULT CURRENT_DATE,
                    tipo_prestador VARCHAR(100) NOT NULL
                )
            """)
            
            # Tabela de datas de envio
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS datas_envio (
                    id SERIAL PRIMARY KEY,
                    tipo_prestador VARCHAR(100) NOT NULL,
                    referencia VARCHAR(50) NOT NULL,
                    faturamento_inicio DATE,
                    faturamento_fim DATE,
                    recurso_inicio DATE,
                    recurso_fim DATE,
                    status VARCHAR(20) DEFAULT 'Ativo',
                    UNIQUE(tipo_prestador, referencia)
                )
            """)
            
            # Tabela de log de envios
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS log_envios (
                    id SERIAL PRIMARY KEY,
                    data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    prestador_id INTEGER REFERENCES prestadores(id),
                    prestador_nome VARCHAR(200),
                    referencia VARCHAR(50),
                    tipo_conta VARCHAR(100),
                    tipo_notificacao VARCHAR(50),
                    sucesso BOOLEAN DEFAULT TRUE,
                    mensagem TEXT
                )
            """)
            
            logger.info("✅ Tabelas criadas/verificadas no NeonDB")
    
    @contextmanager
    def get_cursor(self):
        """Obtém um cursor do pool de conexões"""
        if not self._connection_pool:
            raise Exception("Pool de conexões não disponível")
        
        conn = None
        try:
            conn = self._connection_pool.getconn()
            yield conn.cursor(cursor_factory=RealDictCursor)
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self._connection_pool.putconn(conn)
    
    def get_connection(self):
        """Retorna uma conexão direta (para operações especiais)"""
        if not self._connection_pool:
            return None
        return self._connection_pool.getconn()
    
    def return_connection(self, conn):
        """Devolve conexão ao pool"""
        if conn and self._connection_pool:
            self._connection_pool.putconn(conn)
    
    def close_all(self):
        """Fecha todas as conexões"""
        if self._connection_pool:
            self._connection_pool.closeall()
            logger.info("Pool de conexões fechado")

# Singleton instance
db = NeonDatabase()

# Funções de compatibilidade com o código existente
def get_db_connection():
    """Retorna conexão (compatível com código antigo)"""
    return db.get_connection()

def init_db():
    """Inicializa banco (compatível)"""
    # Já é feito no construtor
    pass