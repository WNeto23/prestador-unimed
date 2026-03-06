import smtplib
import logging
import re
import os
import sys
import time
import psycopg2
import sqlite3
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from datetime import date, timedelta, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from pathlib import Path
from jinja2 import Template
import holidays
from contextlib import contextmanager

# Detecta se está rodando como executável PyInstaller (.exe) ou script normal
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carrega variáveis de ambiente do .env na mesma pasta do executável/script
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Configuração de logging com rotação de arquivos
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("notificacoes.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ====================== CONFIGURAÇÃO DO BANCO ======================
USAR_NEON = os.getenv("NEON_DATABASE_URL") is not None

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
                logger.warning("NEON_DATABASE_URL não configurado, usando SQLite")
                return
            
            # 🔐 CONEXÃO SEGURA COM SSL FORÇADO (exigência do Neon)
            logger.info("🔐 Estabelecendo conexão segura com NeonDB (SSL)")
            self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                dsn=database_url,
                sslmode='require'  # SSL obrigatório para Neon
            )
            logger.info("✅ Pool de conexões NeonDB inicializado com SSL")
            
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

# Instância global do NeonDB
neon_db = NeonDatabase() if USAR_NEON else None

def get_db_connection():
    """Retorna conexão com o banco (Neon com SSL ou SQLite)"""
    if USAR_NEON and neon_db:
        return neon_db.get_connection()
    else:
        db_path = Path(__file__).parent / "prestadores.db"
        return sqlite3.connect(str(db_path))

def return_db_connection(conn):
    """Devolve conexão ao pool (Neon) ou fecha (SQLite)"""
    if USAR_NEON and neon_db and conn:
        neon_db.return_connection(conn)
    elif conn:
        conn.close()

# ====================== CLASSE PRINCIPAL ======================
class Notificador:
    def __init__(self):
        self.email_login = os.getenv("EMAIL_LOGIN")
        self.senha = os.getenv("EMAIL_LOGIN_PASS")
        self.email_remetente = os.getenv("EMAIL_REMETENTE", "prestador@unimedrv.com.br")
        self.url_portal = os.getenv("URL_PORTAL", "https://portal.unimedrv.com.br/PlanodeSaude/index.jsp")
        self.email_contato = os.getenv("EMAIL_CONTATO", "prestador@unimedrv.com.br")
        
        # ========== LOGO ONLINE (URL pública) ==========
        # Opção 1: Logo no GitHub (raw)
        self.logo_url = "https://raw.githubusercontent.com/WNeto23/prestador-unimed/main/logo/logo.jpg"
        
        # Opção 2: Logo no Imgur (comente a de cima e descomente esta se preferir)
        # self.logo_url = "https://i.imgur.com/SUA_LOGO_AQUI.png"
        # ================================================
        
        # Carrega template HTML (compatível com .exe e script normal)
        # Procura primeiro na raiz (ao lado do .exe), depois na subpasta templates/
        template_path = Path(BASE_DIR) / "email_template.html"
        if not template_path.exists():
            template_path = Path(BASE_DIR) / "templates" / "email_template.html"
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                self.template_html = Template(f.read())
        else:
            logger.error(f"Template não encontrado: {template_path}")
            # Template simples de fallback
            self.template_html = Template("""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border-radius: 8px; overflow: hidden; border-left: 6px solid {{ cor_borda }};">
                <div style="background: {{ cor_fundo }}; padding: 20px; text-align: center;">
                    <img src="{{ logo_url }}" alt="Unimed" style="max-width: 200px; margin-bottom: 10px;">
                    <h2 style="margin: 0; color: #333;">{{ icone }} {{ titulo }}</h2>
                </div>
                <div style="padding: 20px;">
                    <table style="width:100%; border-collapse: collapse;">
                        <tr><td style="padding: 8px 0; font-weight: bold;">Prestador:</td><td>{{ prestador }}</td></tr>
                        <tr><td style="padding: 8px 0; font-weight: bold;">Referência:</td><td>{{ referencia }}</td></tr>
                        <tr><td style="padding: 8px 0; font-weight: bold;">Tipo:</td><td>{{ tipo_conta }}</td></tr>
                        {% if data_fim %}<tr><td style="padding: 8px 0; font-weight: bold;">Prazo final:</td><td>{{ data_fim }}</td></tr>{% endif %}
                        {% if dias_restantes %}<tr><td style="padding: 8px 0; font-weight: bold;">Dias restantes:</td><td><strong style="color: {{ cor_borda }};">{{ dias_restantes }}</strong></td></tr>{% endif %}
                    </table>
                    
                    <div style="margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 6px;">
                        {{ mensagem }}
                    </div>
                    
                    {{ msg_especifica }}
                    
                    <div style="text-align: center; margin: 25px 0;">
                        <a href="{{ url_portal }}" style="background: {{ cor_botao }}; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">Acessar Portal</a>
                    </div>
                </div>
                <div style="background: #f0f0f0; padding: 15px; text-align: center; font-size: 12px; color: #666;">
                    Unimed Rio Verde | {{ email_contato }}<br>
                    <small>Este é um e-mail automático. Por favor, não responda.</small>
                </div>
            </div>
            """)
        
        # Carrega feriados brasileiros (para cálculo de dias úteis)
        self.feriados_br = holidays.Brazil()
        
        if not self.email_login or not self.senha:
            logger.warning("⚠️ Credenciais de e-mail não configuradas - modo debug")

    def is_email_valido(self, email: str) -> bool:
        """Valida formato de e-mail"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return bool(re.match(pattern, email.strip()))

    def proximo_dia_util(self, data: date) -> date:
        """Retorna próximo dia útil considerando feriados nacionais"""
        while data.weekday() >= 5 or data in self.feriados_br:
            data += timedelta(days=1)
        return data

    def gerar_ics(self, titulo: str, data_fim: date, tipo_conta: str, prestador: str) -> str:
        """Gera arquivo de calendário .ics para lembretes"""
        agora = datetime.now()
        
        ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Unimed Rio Verde//Notificador//PT
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{agora.timestamp()}@unimedrv.com.br
DTSTAMP:{agora.strftime("%Y%m%dT%H%M%SZ")}
DTSTART;VALUE=DATE:{data_fim.strftime("%Y%m%d")}
DTEND;VALUE=DATE:{data_fim.strftime("%Y%m%d")}
SUMMARY:⚠️ PRAZO FINAL: {tipo_conta} - {prestador}
DESCRIPTION:Prezado(a) {prestador},\n\nEste é um lembrete automático do sistema Unimed.\nHoje é o ÚLTIMO DIA para envio de {tipo_conta} referente a {titulo}.\n\nAcesse o portal: {self.url_portal}
LOCATION:{self.url_portal}
SEQUENCE:0
STATUS:CONFIRMED
TRANSP:OPAQUE
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Lembrete de Prazo - {tipo_conta}
TRIGGER;RELATED=START:-PT2H
END:VALARM
END:VEVENT
END:VCALENDAR"""
        return ics

    def criar_card_email(self, titulo: str, mensagem: str, prestador: str,
                        referencia: str, tipo_conta: str, data_fim: date = None,
                        dias_restantes: int = None, guias_fisicas: list = None) -> str:
        """Renderiza template HTML com os dados e logo online"""
        
        # Define cores baseado no tipo de conta
        if "Recurso" in tipo_conta:
            cor_borda = "#9C27B0"  # Roxo
            cor_fundo = "#F3E5F5"
            icone = "🔄"
            tipo_display = "RECURSO DE GLOSAS"
            msg_especifica = """
                <div style="margin: 15px 0; padding: 12px; background: #f0e6ff; border-radius: 6px;">
                    <p style="margin: 0 0 8px 0; font-weight: bold;">📋 Documentos necessários:</p>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li>Guia de recurso preenchida</li>
                        <li>Cópia da guia glosada</li>
                        <li>Justificativa detalhada</li>
                        <li>Documentação complementar</li>
                    </ul>
                </div>
            """
        else:
            cor_borda = "#007A33"  # Verde Unimed
            cor_fundo = "#E8F5E8"
            icone = "💰"
            tipo_display = "FATURAMENTO DE CONTAS"
            msg_especifica = """
                <div style="margin: 15px 0; padding: 12px; background: #e1f5e1; border-radius: 6px;">
                    <p style="margin: 0;"><strong>⏰ Lembrete:</strong> Guias têm validade de <strong>40 dias</strong> após a execução do procedimento.</p>
                </div>
            """
        
        # Ajusta cores para alertas de prazo
        cor_botao = cor_borda
        if dias_restantes is not None:
            if dias_restantes <= 5:
                cor_borda = "#F44336"  # Vermelho
                cor_fundo = "#FFEBEE"
                icone = "🚨"
                cor_botao = "#D32F2F"
            elif dias_restantes <= 10:
                cor_borda = "#FF9800"  # Laranja
                cor_fundo = "#FFF3E0"
                icone = "⚠️"
                cor_botao = "#F57C00"
        
        # Renderiza template com a logo online
        # Monta lista de datas de guias físicas formatadas para o template
        guias_fmt = []
        for g in (guias_fisicas or []):
            if isinstance(g, date):
                guias_fmt.append(g.strftime("%d/%m/%Y"))
            else:
                try:
                    guias_fmt.append(datetime.strptime(str(g), "%Y-%m-%d").strftime("%d/%m/%Y"))
                except:
                    pass

        return self.template_html.render(
            logo_url=self.logo_url,
            cor_borda=cor_borda,
            cor_fundo=cor_fundo,
            cor_botao=cor_botao,
            icone=icone,
            tipo_display=tipo_display,
            titulo=titulo,
            prestador=prestador,
            referencia=referencia,
            tipo_conta=tipo_conta,
            data_fim=data_fim.strftime("%d/%m/%Y") if data_fim else "",
            dias_restantes=dias_restantes,
            mensagem=mensagem,
            msg_especifica=msg_especifica,
            guias_fisicas=guias_fmt,
            url_portal=self.url_portal,
            email_contato=self.email_contato
        )

    def enviar_email(self, destinatario: str, assunto: str, html_content: str,
                 data_fim: date = None, tipo_conta: str = None, 
                 prestador: str = None, dias_restantes: int = None) -> bool:
        """Envia e-mail com anexo ICS e logo via URL"""
        if not self.is_email_valido(destinatario):
            logger.warning(f"E-mail inválido: {destinatario}")
            return False

        # Modo debug (simulação)
        if not self.email_login or not self.senha:
            logger.info(f"📧 [MODO DEBUG] E-mail seria enviado para: {destinatario}")
            logger.info(f"   Assunto: {assunto}")
            return True

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"Unimed RV <{self.email_remetente}>"
            msg['To'] = destinatario
            msg['Subject'] = assunto
            msg['Reply-To'] = self.email_remetente

            # Parte HTML
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # Anexo ICS (apenas para últimos 5 dias)
            if (data_fim and tipo_conta and prestador and 
                dias_restantes is not None and dias_restantes <= 5):
                
                ics_content = self.gerar_ics(assunto, data_fim, tipo_conta, prestador)
                part_ics = MIMEBase('text', 'calendar', method='PUBLISH', name='lembrete_unimed.ics')
                part_ics.set_payload(ics_content.encode('utf-8'))
                encoders.encode_base64(part_ics)
                part_ics.add_header('Content-Description', 'Lembrete de Prazo')
                part_ics.add_header('Content-Disposition', 'attachment; filename=lembrete_unimed.ics')
                msg.attach(part_ics)

            # Envia via SMTP do Outlook/Office 365
            server = smtplib.SMTP('smtp.office365.com', 587)
            server.starttls()
            server.login(self.email_login, self.senha)
            server.send_message(msg)
            server.quit()

            logger.info(f"✅ E-mail enviado para {destinatario} (De: {self.email_remetente})")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao enviar e-mail: {e}")
            return False

    def registrar_log(self, cursor, prest_id: int, nome: str, ref: str,
                  tipo_conta: str, tipo_notif: str, mensagem: str, sucesso: int = 1):
        """Registra envio no banco (adaptado para PostgreSQL)"""
        try:
            # Converte int (1/0) para booleano PostgreSQL (TRUE/FALSE)
            sucesso_bool = True if sucesso == 1 else False
            
            cursor.execute("""
                INSERT INTO log_envios 
                (prestador_id, prestador_nome, referencia, tipo_conta,
                tipo_notificacao, sucesso, mensagem)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (prest_id, nome, ref, tipo_conta, tipo_notif, sucesso_bool, mensagem[:800]))
        except Exception as e:
            logger.error(f"Erro ao registrar log: {e}")

    def processar_periodo(self, prest_id: int, nome: str, email: str, ref: str,
                          tipo_conta: str, data_inicio_str, data_fim_str,
                          hoje: date, cursor, guias: list = None) -> list:
        """Processa notificações para um período específico"""
        notificacoes = []

        try:
            # PostgreSQL já retorna datetime.date — aceita os dois formatos
            if isinstance(data_inicio_str, date):
                data_inicio = data_inicio_str
            else:
                data_inicio = datetime.strptime(str(data_inicio_str), '%Y-%m-%d').date()

            if isinstance(data_fim_str, date):
                data_fim = data_fim_str
            else:
                data_fim = datetime.strptime(str(data_fim_str), '%Y-%m-%d').date()
        except Exception as e:
            logger.warning(f"Data inválida para {ref} - {tipo_conta}: {e}")
            return notificacoes

        # Verifica se já enviou hoje
        if USAR_NEON:
            cursor.execute("""
                SELECT 1 FROM log_envios 
                WHERE prestador_id = %s AND referencia = %s 
                  AND tipo_conta = %s AND DATE(data_envio) = CURRENT_DATE
            """, (prest_id, ref, tipo_conta))
        else:
            cursor.execute("""
                SELECT 1 FROM log_envios 
                WHERE prestador_id = ? AND referencia = ? 
                  AND tipo_conta = ? AND DATE(data_envio) = DATE('now')
            """, (prest_id, ref, tipo_conta))
        
        if cursor.fetchone():
            logger.debug(f"Já enviou hoje: {nome} - {ref} - {tipo_conta}")
            return notificacoes

        dias_para_fim = (data_fim - hoje).days
        tipo_notif = ""
        assunto = ""
        mensagem = ""

        # Mensagens específicas por tipo de conta
        if "Recurso" in tipo_conta:
            msg_inicio = f"O período para RECURSO DE GLOSAS referente a <strong>{ref}</strong> começou hoje."
            msg_alerta = f"Faltam <strong>{dias_para_fim} dias</strong> para encerrar o período de RECURSO DE GLOSAS."
            msg_urgente = f"🚨 <strong>URGENTE:</strong> Últimos {dias_para_fim} dias para RECURSO DE GLOSAS!"
        else:
            msg_inicio = f"O período de FATURAMENTO referente a <strong>{ref}</strong> começou hoje."
            msg_alerta = f"Faltam <strong>{dias_para_fim} dias</strong> para encerrar o período de FATURAMENTO."
            msg_urgente = f"🚨 <strong>URGENTE:</strong> Últimos {dias_para_fim} dias para FATURAMENTO!"

        # 1. Notificação de INÍCIO do período
        inicio_util = self.proximo_dia_util(data_inicio)
        if hoje == inicio_util:
            tipo_notif = "Inicio"
            assunto = f"✅ Início do período - {ref} - {tipo_conta}"
            mensagem = msg_inicio

        # 2. Alerta de 10 DIAS antes do fim
        elif dias_para_fim == 10:
            alerta_data = data_fim - timedelta(days=10)
            alerta_util = self.proximo_dia_util(alerta_data)
            if hoje == alerta_util:
                tipo_notif = "Alerta_10_dias"
                assunto = f"⚠️ Faltam 10 dias - {ref} - {tipo_conta}"
                mensagem = msg_alerta

        # 3. ÚLTIMOS 5 DIAS (notificação diária)
        elif 1 <= dias_para_fim <= 5:
            tipo_notif = f"Diario_{dias_para_fim}"
            assunto = f"🚨 {dias_para_fim} dia(s) restantes - {ref} - {tipo_conta}"
            mensagem = msg_urgente

        if tipo_notif:
            html = self.criar_card_email(
                titulo=assunto.split(" - ")[0].replace("✅ ", "").replace("⚠️ ", "").replace("🚨 ", ""),
                mensagem=mensagem,
                prestador=nome,
                referencia=ref,
                tipo_conta=tipo_conta,
                data_fim=data_fim,
                dias_restantes=dias_para_fim if dias_para_fim > 0 else None,
                guias_fisicas=guias or []
            )

            enviado = self.enviar_email(
                destinatario=email,
                assunto=assunto,
                html_content=html,
                data_fim=data_fim if dias_para_fim <= 5 else None,
                tipo_conta=tipo_conta,
                prestador=nome,
                dias_restantes=dias_para_fim
            )

            self.registrar_log(
                cursor=cursor,
                prest_id=prest_id,
                nome=nome,
                ref=ref,
                tipo_conta=tipo_conta,
                tipo_notif=tipo_notif,
                mensagem=mensagem,
                sucesso=1 if enviado else 0
            )

            if enviado:
                notificacoes.append(f"{tipo_notif} → {nome}")

        return notificacoes

    def _executar_notificacoes(self, cursor):
        """Lógica principal de execução (reutilizável)"""
        hoje = date.today()
        notificacoes_enviadas = []
        
        logger.info(f"📅 Data da execução: {hoje.strftime('%d/%m/%Y')}")
        
        # Query para buscar prestadores ativos com seus períodos
        if USAR_NEON:
            cursor.execute("""
                SELECT p.id, p.nome, p.email, p.tipo_prestador,
                       d.referencia, d.faturamento_inicio, d.faturamento_fim,
                       d.recurso_inicio, d.recurso_fim,
                       d.guia_fisica_1, d.guia_fisica_2, d.guia_fisica_3, d.guia_fisica_4
                FROM prestadores p
                JOIN datas_envio d ON p.tipo_prestador = d.tipo_prestador
                WHERE d.status = 'Ativo'
            """)
        else:
            cursor.execute("""
                SELECT p.id, p.nome, p.email, p.tipo_prestador,
                       d.referencia, d.faturamento_inicio, d.faturamento_fim,
                       d.recurso_inicio, d.recurso_fim,
                       NULL, NULL, NULL, NULL
                FROM prestadores p
                JOIN datas_envio d ON p.tipo_prestador = d.tipo_prestador
                WHERE d.status = 'Ativo'
            """)
        
        registros = cursor.fetchall()
        logger.info(f"📊 Encontrados {len(registros)} prestadores ativos")
        
        for idx, row in enumerate(registros):
            if USAR_NEON:
                prest_id = row['id']
                nome = row['nome']
                email = row['email']
                ref = row['referencia']
                fat_ini = row['faturamento_inicio']
                fat_fim = row['faturamento_fim']
                rec_ini = row['recurso_inicio']
                rec_fim = row['recurso_fim']
                guias = [row.get('guia_fisica_1'), row.get('guia_fisica_2'),
                         row.get('guia_fisica_3'), row.get('guia_fisica_4')]
                guias = [g for g in guias if g]  # remove None
            else:
                prest_id, nome, email, _, ref, fat_ini, fat_fim, rec_ini, rec_fim, *_ = row
                guias = []
            
            # Valida e-mail
            if not self.is_email_valido(email):
                logger.warning(f"⚠️ E-mail inválido para {nome}: {email}")
                continue
            
            logger.info(f"📧 Processando: {nome} - {ref}")
            
            # Processa Faturamento
            if fat_ini and fat_fim:
                enviadas = self.processar_periodo(
                    prest_id, nome, email, ref, "Faturamento Contas",
                    fat_ini, fat_fim, hoje, cursor, guias
                )
                notificacoes_enviadas.extend(enviadas)
            
            # Processa Recurso de Glosas
            if rec_ini and rec_fim:
                enviadas = self.processar_periodo(
                    prest_id, nome, email, ref, "Recurso de Glosas",
                    rec_ini, rec_fim, hoje, cursor, guias
                )
                notificacoes_enviadas.extend(enviadas)
                notificacoes_enviadas.extend(enviadas)
            
            # Delay entre prestadores para evitar bloqueio
            if enviadas and idx < len(registros) - 1:
                time.sleep(1.5)
        
        return notificacoes_enviadas

    def verificar_e_notificar(self):
        """Função principal - executa notificações com NeonDB (SSL) ou SQLite"""
        logger.info("="*50)
        logger.info("🚀 INICIANDO SISTEMA DE NOTIFICAÇÕES")
        logger.info(f"📦 Banco: {'NeonDB (PostgreSQL com SSL)' if USAR_NEON else 'SQLite local'}")
        
        if USAR_NEON and neon_db:
            # Para Neon, usa o context manager com SSL
            with neon_db.get_cursor() as cursor:
                notificacoes = self._executar_notificacoes(cursor)
                logger.info(f"📨 Total de notificações enviadas: {len(notificacoes)}")
                logger.info("="*50)
                return notificacoes
        else:
            # Para SQLite, mantém o código atual
            conn = self.get_db_connection()
            cursor = conn.cursor()
            try:
                notificacoes = self._executar_notificacoes(cursor)
                conn.commit()
                logger.info(f"📨 Total de notificações enviadas: {len(notificacoes)}")
                logger.info("="*50)
                return notificacoes
            except Exception as e:
                conn.rollback()
                logger.error(f"❌ Erro fatal: {e}", exc_info=True)
                raise
            finally:
                conn.close()

# ====================== PONTO DE ENTRADA ======================
if __name__ == "__main__":
    try:
        notificador = Notificador()
        notificador.verificar_e_notificar()
    except Exception as e:
        logger.error(f"❌ Falha na execução: {e}", exc_info=True)
        raise