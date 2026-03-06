import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os
import logging
from contextlib import contextmanager
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NeonDatabase:
    """Gerenciador de conexão com NeonDB (PostgreSQL) com SSL forçado"""
    
    _instance = None
    _connection_pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self):
        """Inicializa o pool de conexões com SSL obrigatório"""
        try:
            database_url = os.getenv("NEON_DATABASE_URL")
            if not database_url:
                raise ValueError("NEON_DATABASE_URL não encontrado no .env")
            
            # 🔐 CONEXÃO SEGURA COM SSL FORÇADO
            logger.info("🔐 Estabelecendo conexão segura com NeonDB (SSL)")
            self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                dsn=database_url,
                sslmode='require'
            )
            logger.info("✅ Pool de conexões NeonDB inicializado com SSL")
            
            # Cria tabelas se não existirem
            self._create_tables()
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao NeonDB: {e}")
            raise  # Re-lança a exceção para parar o programa
    
    def _create_tables(self):
        """Cria as tabelas no PostgreSQL se não existirem"""
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
                    guia_fisica_1 DATE,
                    guia_fisica_2 DATE,
                    guia_fisica_3 DATE,
                    guia_fisica_4 DATE,
                    guia_fisica_5 DATE,
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
        """Retorna uma conexão direta do pool"""
        if not self._connection_pool:
            raise Exception("Pool de conexões não disponível")
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

# ====================== EXPORTAÇÕES ======================
# Cria a instância única do banco
try:
    neon_db = NeonDatabase()
    USAR_NEON = True
    logger.info("✅ NeonDB inicializado com sucesso!")
except Exception as e:
    logger.error(f"❌ Falha ao inicializar NeonDB: {e}")
    neon_db = None
    USAR_NEON = False
    raise  # Re-lança para parar o programa