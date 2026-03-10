import smtplib
import logging
import re
import os
import sys
import time
from datetime import date, timedelta, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from pathlib import Path
from jinja2 import Template
import holidays

# Detecta se está rodando como executável PyInstaller (.exe) ou script normal
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carrega variáveis de ambiente do .env na mesma pasta do executável/script
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Configuração de logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("notificacoes.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ====================== CLIENTE DA API ======================
try:
    from api_client import (
        listar_prestadores, listar_datas_envio, registrar_log
    )
    logger.info("✅ api_client carregado no notificador")
except ImportError as e:
    logger.error(f"❌ ERRO CRÍTICO: api_client não disponível - {e}")
    sys.exit(1)


# ====================== CLASSE PRINCIPAL ======================
class Notificador:
    def __init__(self):
        self.email_login      = os.getenv("EMAIL_LOGIN")
        self.senha            = os.getenv("EMAIL_LOGIN_PASS")
        self.email_remetente  = os.getenv("EMAIL_REMETENTE", "prestador@unimedrv.com.br")
        self.url_portal       = os.getenv("URL_PORTAL", "https://portal.unimedrv.com.br/PlanodeSaude/index.jsp")
        self.email_contato    = os.getenv("EMAIL_CONTATO", "prestador@unimedrv.com.br")

        # Logo pública (GitHub raw)
        self.logo_url = "https://raw.githubusercontent.com/WNeto23/prestador-unimed/main/logo/logo.jpg"

        # Carrega template HTML (ao lado do .exe ou em templates/)
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
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;
                        border-radius: 8px; overflow: hidden; border-left: 6px solid {{ cor_borda }};">
                <div style="background: {{ cor_fundo }}; padding: 20px; text-align: center;">
                    <img src="{{ logo_url }}" alt="Unimed" style="max-width: 200px; margin-bottom: 10px;">
                    <h2 style="margin: 0; color: #333;">{{ icone }} {{ titulo }}</h2>
                </div>
                <div style="padding: 20px;">
                    <table style="width:100%; border-collapse: collapse;">
                        <tr><td style="padding:8px 0;font-weight:bold;">Prestador:</td><td>{{ prestador }}</td></tr>
                        <tr><td style="padding:8px 0;font-weight:bold;">Referência:</td><td>{{ referencia }}</td></tr>
                        <tr><td style="padding:8px 0;font-weight:bold;">Tipo:</td><td>{{ tipo_conta }}</td></tr>
                        {% if data_fim %}<tr><td style="padding:8px 0;font-weight:bold;">Prazo final:</td>
                        <td>{{ data_fim }}</td></tr>{% endif %}
                        {% if dias_restantes %}<tr><td style="padding:8px 0;font-weight:bold;">Dias restantes:</td>
                        <td><strong style="color:{{ cor_borda }};">{{ dias_restantes }}</strong></td></tr>{% endif %}
                    </table>
                    <div style="margin:20px 0;padding:15px;background:#f5f5f5;border-radius:6px;">
                        {{ mensagem }}
                    </div>
                    {{ msg_especifica }}
                    <div style="text-align:center;margin:25px 0;">
                        <a href="{{ url_portal }}" style="background:{{ cor_botao }};color:white;
                           padding:12px 25px;text-decoration:none;border-radius:5px;
                           font-weight:bold;">Acessar Portal</a>
                    </div>
                </div>
                <div style="background:#f0f0f0;padding:15px;text-align:center;font-size:12px;color:#666;">
                    Unimed Rio Verde | {{ email_contato }}<br>
                    <small>Este é um e-mail automático. Por favor, não responda.</small>
                </div>
            </div>
            """)

        # Feriados brasileiros
        self.feriados_br = holidays.Brazil()

        if not self.email_login or not self.senha:
            logger.warning("⚠️ Credenciais de e-mail não configuradas - modo debug")

    # ====================== UTILITÁRIOS ======================

    def is_email_valido(self, email: str) -> bool:
        if not email:
            return False
        return bool(re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email.strip()))

    def proximo_dia_util(self, data: date) -> date:
        while data.weekday() >= 5 or data in self.feriados_br:
            data += timedelta(days=1)
        return data

    def gerar_ics(self, titulo: str, data_fim: date, tipo_conta: str, prestador: str) -> str:
        agora = datetime.now()
        return f"""BEGIN:VCALENDAR
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
DESCRIPTION:Prezado(a) {prestador},\\n\\nEste é um lembrete automático do sistema Unimed.\\nHoje é o ÚLTIMO DIA para envio de {tipo_conta} referente a {titulo}.\\n\\nAcesse o portal: {self.url_portal}
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

    # ====================== TEMPLATE DE E-MAIL ======================

    def criar_card_email(self, titulo: str, mensagem: str, prestador: str,
                         referencia: str, tipo_conta: str, data_fim: date = None,
                         dias_restantes: int = None, guias_fisicas: list = None) -> str:
        """Renderiza template HTML com os dados"""

        if "Recurso" in tipo_conta:
            cor_borda = "#9C27B0"; cor_fundo = "#F3E5F5"; icone = "🔄"
            tipo_display = "RECURSO DE GLOSAS"
            msg_especifica = """
                <div style="margin:15px 0;padding:12px;background:#f0e6ff;border-radius:6px;">
                    <p style="margin:0 0 8px 0;font-weight:bold;">📋 Documentos necessários:</p>
                    <ul style="margin:0;padding-left:20px;">
                        <li>Guia de recurso preenchida</li>
                        <li>Cópia da guia glosada</li>
                        <li>Justificativa detalhada</li>
                        <li>Documentação complementar</li>
                    </ul>
                </div>"""
        else:
            cor_borda = "#007A33"; cor_fundo = "#E8F5E8"; icone = "💰"
            tipo_display = "FATURAMENTO DE CONTAS"
            msg_especifica = """
                <div style="margin:15px 0;padding:12px;background:#e1f5e1;border-radius:6px;">
                    <p style="margin:0;"><strong>⏰ Lembrete:</strong> Guias têm validade de
                    <strong>40 dias</strong> após a execução do procedimento.</p>
                </div>"""

        cor_botao = cor_borda
        if dias_restantes is not None:
            if dias_restantes <= 5:
                cor_borda = "#F44336"; cor_fundo = "#FFEBEE"; icone = "🚨"; cor_botao = "#D32F2F"
            elif dias_restantes <= 10:
                cor_borda = "#FF9800"; cor_fundo = "#FFF3E0"; icone = "⚠️"; cor_botao = "#F57C00"

        # Formata datas de guias físicas
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
            cor_borda=cor_borda, cor_fundo=cor_fundo, cor_botao=cor_botao,
            icone=icone, tipo_display=tipo_display,
            titulo=titulo, prestador=prestador, referencia=referencia,
            tipo_conta=tipo_conta,
            data_fim=data_fim.strftime("%d/%m/%Y") if data_fim else "",
            dias_restantes=dias_restantes,
            mensagem=mensagem, msg_especifica=msg_especifica,
            guias_fisicas=guias_fmt,
            url_portal=self.url_portal,
            email_contato=self.email_contato
        )

    # ====================== ENVIO DE E-MAIL ======================

    def enviar_email(self, destinatario: str, assunto: str, html_content: str,
                     data_fim: date = None, tipo_conta: str = None,
                     prestador: str = None, dias_restantes: int = None) -> bool:
        if not self.is_email_valido(destinatario):
            logger.warning(f"E-mail inválido: {destinatario}")
            return False

        # Modo debug (sem credenciais)
        if not self.email_login or not self.senha:
            logger.info(f"📧 [MODO DEBUG] E-mail seria enviado para: {destinatario} | {assunto}")
            return True

        try:
            msg = MIMEMultipart('alternative')
            msg['From']     = f"Unimed RV <{self.email_remetente}>"
            msg['To']       = destinatario
            msg['Subject']  = assunto
            msg['Reply-To'] = self.email_remetente
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # Anexo ICS apenas nos últimos 5 dias
            if (data_fim and tipo_conta and prestador and
                    dias_restantes is not None and dias_restantes <= 5):
                ics = self.gerar_ics(assunto, data_fim, tipo_conta, prestador)
                part = MIMEBase('text', 'calendar', method='PUBLISH', name='lembrete_unimed.ics')
                part.set_payload(ics.encode('utf-8'))
                encoders.encode_base64(part)
                part.add_header('Content-Description', 'Lembrete de Prazo')
                part.add_header('Content-Disposition', 'attachment; filename=lembrete_unimed.ics')
                msg.attach(part)

            server = smtplib.SMTP('smtp.office365.com', 587)
            server.starttls()
            server.login(self.email_login, self.senha)
            server.send_message(msg)
            server.quit()
            logger.info(f"✅ E-mail enviado para {destinatario}")
            return True

        except Exception as e:
            logger.error(f"❌ Erro ao enviar e-mail: {e}")
            return False

    # ====================== LÓGICA DE NOTIFICAÇÃO ======================

    def _ja_enviou_hoje(self, prest_id: int, ref: str, tipo_conta: str) -> bool:
        """Verifica via API se já foi enviado hoje para este prestador/período/tipo"""
        from api_client import api_get
        hoje_str = date.today().isoformat()
        try:
            logs = api_get("/log")
            for log in logs:
                if (log.get("prestador_id") == prest_id and
                        log.get("referencia") == ref and
                        log.get("tipo_conta") == tipo_conta and
                        log.get("data_envio", "")[:10] == hoje_str):
                    return True
        except Exception as e:
            logger.warning(f"Não foi possível verificar log: {e}")
        return False

    def processar_periodo(self, prest_id: int, nome: str, email: str, ref: str,
                          tipo_conta: str, data_inicio_str, data_fim_str,
                          hoje: date, guias: list = None) -> list:
        """Processa notificações para um período específico"""
        notificacoes = []

        try:
            data_inicio = data_inicio_str if isinstance(data_inicio_str, date) \
                else datetime.strptime(str(data_inicio_str), '%Y-%m-%d').date()
            data_fim = data_fim_str if isinstance(data_fim_str, date) \
                else datetime.strptime(str(data_fim_str), '%Y-%m-%d').date()
        except Exception as e:
            logger.warning(f"Data inválida para {ref} - {tipo_conta}: {e}")
            return notificacoes

        # Verifica se já enviou hoje
        if self._ja_enviou_hoje(prest_id, ref, tipo_conta):
            logger.debug(f"Já enviou hoje: {nome} - {ref} - {tipo_conta}")
            return notificacoes

        dias_para_fim = (data_fim - hoje).days
        fat_ini_fmt   = data_inicio.strftime("%d/%m/%Y")
        fat_fim_fmt   = data_fim.strftime("%d/%m/%Y")

        if "Recurso" in tipo_conta:
            msg_inicio  = (f"O período para <strong>RECURSO DE GLOSAS</strong> referente a "
                           f"<strong>{ref}</strong> começou hoje.<br><br>"
                           f"📅 Período: <strong>{fat_ini_fmt}</strong> até <strong>{fat_fim_fmt}</strong><br>"
                           f"Você tem <strong>{dias_para_fim} dias</strong> para realizar o envio.")
            msg_alerta  = f"Faltam <strong>{dias_para_fim} dias</strong> para encerrar o RECURSO DE GLOSAS."
            msg_urgente = f"🚨 <strong>URGENTE:</strong> Últimos {dias_para_fim} dias para RECURSO DE GLOSAS!"
        else:
            msg_inicio  = (f"O período de <strong>FATURAMENTO DE CONTAS</strong> referente a "
                           f"<strong>{ref}</strong> começou hoje.<br><br>"
                           f"📅 Período: <strong>{fat_ini_fmt}</strong> até <strong>{fat_fim_fmt}</strong><br>"
                           f"Você tem <strong>{dias_para_fim} dias</strong> para realizar o envio das contas.")
            msg_alerta  = f"Faltam <strong>{dias_para_fim} dias</strong> para encerrar o FATURAMENTO."
            msg_urgente = f"🚨 <strong>URGENTE:</strong> Últimos {dias_para_fim} dias para FATURAMENTO!"

        tipo_notif = ""; assunto = ""; mensagem = ""

        # 1. Início do período
        if hoje == self.proximo_dia_util(data_inicio):
            tipo_notif = "Inicio"
            assunto    = f"✅ Início do período - {ref} - {tipo_conta}"
            mensagem   = msg_inicio

        # 2. Alerta 10 dias antes
        elif dias_para_fim == 10:
            if hoje == self.proximo_dia_util(data_fim - timedelta(days=10)):
                tipo_notif = "Alerta_10_dias"
                assunto    = f"⚠️ Faltam 10 dias - {ref} - {tipo_conta}"
                mensagem   = msg_alerta

        # 3. Últimos 5 dias (diário)
        elif 1 <= dias_para_fim <= 5:
            tipo_notif = f"Diario_{dias_para_fim}"
            assunto    = f"🚨 {dias_para_fim} dia(s) restantes - {ref} - {tipo_conta}"
            mensagem   = msg_urgente

        if tipo_notif:
            html = self.criar_card_email(
                titulo=assunto.split(" - ")[0].replace("✅ ","").replace("⚠️ ","").replace("🚨 ",""),
                mensagem=mensagem, prestador=nome, referencia=ref,
                tipo_conta=tipo_conta, data_fim=data_fim,
                dias_restantes=dias_para_fim if dias_para_fim > 0 else None,
                guias_fisicas=guias or []
            )
            enviado = self.enviar_email(
                destinatario=email, assunto=assunto, html_content=html,
                data_fim=data_fim if dias_para_fim <= 5 else None,
                tipo_conta=tipo_conta, prestador=nome, dias_restantes=dias_para_fim
            )

            # Registra log via API
            try:
                registrar_log(
                    prestador_id=prest_id, prestador_nome=nome,
                    referencia=ref, tipo_conta=tipo_conta,
                    tipo_notificacao=tipo_notif,
                    sucesso=enviado, mensagem=mensagem[:800]
                )
            except Exception as e:
                logger.error(f"Erro ao registrar log: {e}")

            if enviado:
                notificacoes.append(f"{tipo_notif} → {nome}")

        return notificacoes

    # ====================== EXECUÇÃO PRINCIPAL ======================

    def verificar_e_notificar(self):
        """Função principal — busca dados via API e processa notificações"""
        logger.info("=" * 50)
        logger.info("🚀 INICIANDO SISTEMA DE NOTIFICAÇÕES")
        logger.info("🌐 Banco: API Railway → NeonDB")

        hoje = date.today()
        logger.info(f"📅 Data da execução: {hoje.strftime('%d/%m/%Y')}")

        notificacoes_enviadas = []

        try:
            # Busca todos os prestadores e períodos ativos via API
            prestadores = listar_prestadores()   # [(id, codigo, nome, email, tipo, data_cad)]
            datas_ativas = [
                row for row in listar_datas_envio()
                if row[7] == "Ativo"              # índice 7 = status
            ]

            logger.info(f"👥 Prestadores: {len(prestadores)} | 📅 Períodos ativos: {len(datas_ativas)}")

            for idx, prest in enumerate(prestadores):
                prest_id, _, nome, email, tipo_prest, _ = prest

                if not self.is_email_valido(email):
                    logger.warning(f"⚠️ E-mail inválido: {nome} <{email}>")
                    continue

                # Filtra períodos do tipo deste prestador
                periodos = [d for d in datas_ativas if d[1] == tipo_prest]

                for periodo in periodos:
                    # listar_datas_envio retorna:
                    # (id, tipo_prest, ref, fat_ini, fat_fim, rec_ini, rec_fim, status,
                    #  guia1, guia2, guia3, guia4, guia5)
                    _, _, ref, fat_ini, fat_fim, rec_ini, rec_fim, _, g1, g2, g3, g4, g5 = periodo
                    guias = [g for g in [g1, g2, g3, g4, g5] if g]

                    logger.info(f"📧 Processando: {nome} - {ref}")

                    enviadas = []

                    # Faturamento de Contas
                    if fat_ini and fat_fim:
                        enviadas += self.processar_periodo(
                            prest_id, nome, email, ref,
                            "Faturamento Contas", fat_ini, fat_fim, hoje, guias)

                    # Recurso de Glosas
                    if rec_ini and rec_fim:
                        enviadas += self.processar_periodo(
                            prest_id, nome, email, ref,
                            "Recurso de Glosas", rec_ini, rec_fim, hoje, guias)

                    notificacoes_enviadas.extend(enviadas)

                    # Delay entre envios
                    if enviadas and idx < len(prestadores) - 1:
                        time.sleep(1.5)

        except Exception as e:
            logger.error(f"❌ Erro fatal: {e}", exc_info=True)
            raise

        logger.info(f"📨 Total de notificações enviadas: {len(notificacoes_enviadas)}")
        logger.info("=" * 50)
        return notificacoes_enviadas


# ====================== PONTO DE ENTRADA ======================
if __name__ == "__main__":
    try:
        notificador = Notificador()
        notificador.verificar_e_notificar()
    except Exception as e:
        logger.error(f"❌ Falha na execução: {e}", exc_info=True)
        raise