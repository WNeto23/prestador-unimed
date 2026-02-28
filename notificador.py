import smtplib
import logging
import re
import sqlite3
import base64
from datetime import date, timedelta, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from dotenv import load_dotenv
import os

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("notificacoes.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class Notificador:
    def __init__(self):
        # Credenciais para login no SMTP
        self.email_login = os.getenv("EMAIL_LOGIN")
        self.senha = os.getenv("EMAIL_LOGIN_PASS")
        
        # E-mail que aparecerá como remetente
        self.email_remetente = os.getenv("EMAIL_REMETENTE", "prestador@unimedrv.com.br")
        
        # Caminho do logo
        self.logo_path = r'C:\Users\waltuiro.neto\OneDrive - Unimed Rio Verde\envio_de_notificacao_faturamento\logo\logo_unimed'
        
        if not self.email_login or not self.senha:
            logger.error("Credenciais de e-mail não encontradas no .env (EMAIL_LOGIN / EMAIL_LOGIN_PASS)")
            logger.warning("Continuando sem e-mail - modo debug")
    
    def get_logo_base64(self):
        """Converte o logo para base64 para embed no HTML"""
        try:
            # Tenta diferentes extensões
            for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                caminho = self.logo_path + ext
                if os.path.exists(caminho):
                    with open(caminho, 'rb') as f:
                        logo_data = f.read()
                        logo_base64 = base64.b64encode(logo_data).decode('utf-8')
                        mime_type = f"image/{ext[1:]}"
                        return f"data:{mime_type};base64,{logo_base64}"
            
            logger.warning(f"Logo não encontrado em: {self.logo_path}")
            return None
        except Exception as e:
            logger.error(f"Erro ao carregar logo: {e}")
            return None
    
    def is_email_valido(self, email: str) -> bool:
        """Validação simples de formato de e-mail"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return bool(re.match(pattern, email.strip()))

    def proximo_dia_util(self, data: date) -> date:
        """Retorna o próximo dia útil (seg-sex) após a data informada"""
        while data.weekday() >= 5:  # 5=sáb, 6=dom
            data += timedelta(days=1)
        return data

    def criar_card_email(self, titulo: str, mensagem: str, prestador: str,
                        referencia: str, tipo_conta: str, dias_restantes: int = None) -> str:
        """Gera HTML bonito para o e-mail (card style) com logo da Unimed"""
        
        # Define cores baseado no tipo de conta
        if "Recurso" in tipo_conta:
            cor_borda = "#9C27B0"  # Roxo para recurso de glosas
            cor_fundo = "#F3E5F5"
            icone = "🔄"
            tipo_display = "RECURSO DE GLOSAS"
        else:
            cor_borda = "#007A33"  # Verde Unimed para faturamento
            cor_fundo = "#E8F5E8"
            icone = "💰"
            tipo_display = "FATURAMENTO DE CONTAS"
        
        # Ajusta cor baseado nos dias restantes (sobrescreve se necessário)
        if dias_restantes is not None:
            if dias_restantes <= 5:
                cor_borda = "#F44336"   # vermelho
                cor_fundo = "#FFEBEE"
                icone = "🚨"
            elif dias_restantes <= 10:
                cor_borda = "#FF9800"   # laranja
                cor_fundo = "#FFF3E0"
                icone = "⚠️"
        
        # Carrega logo
        logo_base64 = self.get_logo_base64()
        logo_html = f'<img src="{logo_base64}" alt="Unimed RV" style="height: 60px; margin-bottom: 10px;">' if logo_base64 else '<h2 style="color: #007A33;">Unimed Rio Verde</h2>'
        
        # Mensagens específicas para cada tipo
        if "Recurso" in tipo_conta:
            msg_especifica = (
                "<p style='margin-top: 15px;'><strong>Documentos necessários para recurso:</strong></p>"
                "<ul style='margin-top: 5px;'>"
                "<li>Guia de recurso preenchida</li>"
                "<li>Cópia da guia glosada</li>"
                "<li>Justificativa do recurso</li>"
                "<li>Documentação complementar (se houver)</li>"
                "</ul>"
            )
        else:
            msg_especifica = (
                "<p style='margin-top: 15px;'><strong>Lembrete:</strong> As guias têm validade de "
                "<span style='color: #007A33; font-weight: bold;'>40 dias</span> após a execução do procedimento.</p>"
            )

        html = f"""
        <div style="font-family: Arial, Helvetica, sans-serif; max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
            <!-- Cabeçalho com logo -->
            <div style="background: #f8f8f8; padding: 20px; text-align: center; border-bottom: 3px solid {cor_borda};">
                {logo_html}
                <div style="background: {cor_borda}; color: white; padding: 8px 15px; border-radius: 20px; display: inline-block; font-size: 14px; font-weight: bold; margin-top: 10px;">
                    {tipo_display}
                </div>
            </div>
            
            <!-- Título com ícone -->
            <div style="background: {cor_fundo}; padding: 24px 20px;">
                <h2 style="margin: 0; color: #1a1a1a; font-size: 22px; text-align: center;">{icone} {titulo}</h2>
            </div>
            
            <!-- Conteúdo principal -->
            <div style="padding: 24px 20px; color: #333;">
                <table style="width:100%; border-collapse: collapse;">
                    <tr><td style="padding: 8px 0; font-weight: bold; width: 140px;">👤 Prestador:</td><td>{prestador}</td></tr>
                    <tr><td style="padding: 8px 0; font-weight: bold;">📅 Referência:</td><td>{referencia}</td></tr>
                    <tr><td style="padding: 8px 0; font-weight: bold;">📋 Tipo:</td><td>{tipo_conta}</td></tr>
                    {f'<tr><td style="padding: 8px 0; font-weight: bold;">⏰ Dias restantes:</td><td><span style="background: {cor_borda}; color: white; padding: 3px 10px; border-radius: 12px;">{dias_restantes}</span></td></tr>' if dias_restantes is not None else ''}
                </table>
                
                <div style="margin: 24px 0; padding: 16px; background: #f8f9fa; border-radius: 6px; line-height: 1.6;">
                    {mensagem.replace('\n', '<br>')}
                </div>
                
                {msg_especifica}
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px dashed #ccc; text-align: center;">
                    <p style="font-size: 12px; color: #999;">
                        📍 R. Qualquer, 123 - Centro, Rio Verde - GO<br>
                        📞 (64) 1234-5678 | 📧 prestador@unimedrv.com.br
                    </p>
                    <p style="font-size: 11px; color: #ccc; margin-top: 15px;">
                        Este é um e-mail automático do sistema de notificações. Por favor, não responda esta mensagem.<br>
                        Em caso de dúvidas, entre em contato com seu gestor.
                    </p>
                </div>
            </div>
        </div>
        """
        return html

    def enviar_email(self, destinatario: str, assunto: str, html_content: str) -> bool:
        """Envia e-mail via SMTP Office 365 / Outlook usando login diferente do remetente"""
        if not self.is_email_valido(destinatario):
            logger.warning(f"E-mail inválido, pulando envio: {destinatario}")
            return False

        if not self.email_login or not self.senha:
            logger.warning("Credenciais de e-mail não configuradas. Modo simulação.")
            print(f"\n📧 SIMULAÇÃO DE E-MAIL:")
            print(f"   De: {self.email_remetente} (autenticado como: {self.email_login})")
            print(f"   Para: {destinatario}")
            print(f"   Assunto: {assunto}")
            print(f"   HTML: {len(html_content)} caracteres\n")
            return True  # Simula sucesso

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = f"Unimed RV <{self.email_remetente}>"  # Quem aparece como remetente
            msg['To'] = destinatario
            msg['Subject'] = assunto
            msg['Reply-To'] = self.email_remetente  # Respostas vão para o e-mail oficial

            # fallback texto
            text_part = "Este e-mail requer visualização em cliente compatível com HTML."
            msg.attach(MIMEText(text_part, 'plain'))

            # HTML principal
            msg.attach(MIMEText(html_content, 'html'))

            # Conecta usando as credenciais de login
            server = smtplib.SMTP('smtp.office365.com', 587)
            server.starttls()
            server.login(self.email_login, self.senha)  # Login com suas credenciais
            server.send_message(msg)
            server.quit()

            logger.info(f"E-mail enviado com sucesso para {destinatario} | Assunto: {assunto}")
            return True

        except Exception as e:
            logger.error(f"Falha ao enviar e-mail para {destinatario}: {str(e)}", exc_info=True)
            return False

    def get_db_connection(self):
        """Cria conexão direta com o banco"""
        return sqlite3.connect("prestadores.db")

    def registrar_log(self, cursor, prest_id: int, nome: str, ref: str,
                      tipo_conta: str, tipo_notif: str, mensagem: str, sucesso: int = 1):
        """Registra envio no banco de dados"""
        try:
            cursor.execute('''
                INSERT INTO log_envios 
                (prestador_id, prestador_nome, referencia, tipo_conta,
                 tipo_notificacao, sucesso, mensagem)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (prest_id, nome, ref, tipo_conta, tipo_notif, sucesso, mensagem[:800]))
        except Exception as e:
            logger.error(f"Erro ao registrar log: {e}")

    def processar_periodo(self, prest_id: int, nome: str, email: str, ref: str,
                          tipo_conta: str, data_inicio_str: str, data_fim_str: str,
                          hoje: date, cursor) -> list:
        """Processa notificações para um período específico (faturamento ou recurso)"""
        notificacoes = []

        try:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except Exception as e:
            logger.warning(f"Data inválida para {ref} - {tipo_conta}: {e}")
            return notificacoes

        # Já enviou hoje para este prestador/referencia/tipo_conta?
        cursor.execute('''
            SELECT 1 FROM log_envios 
            WHERE prestador_id = ? 
              AND referencia = ? 
              AND tipo_conta = ? 
              AND DATE(data_envio) = DATE('now')
        ''', (prest_id, ref, tipo_conta))
        if cursor.fetchone():
            logger.debug(f"Já enviou hoje: {nome} - {ref} - {tipo_conta}")
            return notificacoes

        dias_para_fim = (data_fim - hoje).days
        tipo_notif = ""
        assunto = ""
        mensagem = ""

        # Mensagens específicas para Recurso de Glosas
        if "Recurso" in tipo_conta:
            msg_inicio = (
                "O período para <strong>RECURSO DE GLOSAS</strong> da referência <strong>{}</strong> começou hoje.<br><br>"
                "Caso tenha recebido glosas no faturamento anterior, este é o momento para apresentar seus recursos.<br><br>"
                "Documentos necessários:<br>"
                "• Guia de recurso preenchida<br>"
                "• Cópia da guia glosada<br>"
                "• Justificativa detalhada do recurso<br>"
                "• Documentação complementar que comprove a correção"
            ).format(ref)
            
            msg_alerta = (
                "Faltam <strong>{} dia(s)</strong> para o encerramento do período de <strong>RECURSO DE GLOSAS</strong>.<br><br>"
                "• Verifique se todos os recursos estão prontos<br>"
                "• Confira a documentação de cada guia glosada<br>"
                "• Organize os recursos por lote/prestador"
            )
            
            msg_urgente = (
                "🚨 <strong>ÚLTIMOS DIAS PARA RECURSO DE GLOSAS!</strong><br><br>"
                "Restam apenas <strong>{} dia(s)</strong> para encerramento.<br><br>"
                "• Não deixe para última hora<br>"
                "• Confira se todos os recursos foram protocolados<br>"
                "• Guarde os comprovantes de envio"
            )
        else:
            msg_inicio = (
                "Informamos que o período de envio de contas para a referência <strong>{}</strong> "
                "teve início hoje (ou no próximo dia útil).<br><br>"
                "Organize suas guias com antecedência. Lembre-se: as guias possuem validade de "
                "<strong>40 dias</strong> após a execução do procedimento."
            ).format(ref)
            
            msg_alerta = (
                "Faltam <strong>{} dia(s)</strong> para o fim do período de envio da referência <strong>{}</strong>.<br><br>"
                "• Organize as contas pendentes<br>"
                "• Verifique se todas as guias estão dentro do prazo de 40 dias<br>"
                "• Evite deixar para os últimos dias"
            )
            
            msg_urgente = (
                "ATENÇÃO! Restam apenas <strong>{} dia(s)</strong> para o encerramento do período.<br><br>"
                "• Envie suas contas o quanto antes<br>"
                "• Confirme a validade das guias (40 dias após execução)<br>"
                "• Certifique-se de que toda a documentação está completa"
            )

        # 1. Início do período
        inicio_util = self.proximo_dia_util(data_inicio)
        if hoje == inicio_util:
            tipo_notif = "Inicio"
            assunto = f"✅ Início do período - {ref} - {tipo_conta}"
            mensagem = msg_inicio

        # 2. Alerta de 10 dias
        elif dias_para_fim == 10:
            alerta_data = data_fim - timedelta(days=10)
            alerta_util = self.proximo_dia_util(alerta_data)
            if hoje == alerta_util:
                tipo_notif = "Alerta_10_dias"
                assunto = f"⚠️ Faltam 10 dias - {ref} - {tipo_conta}"
                mensagem = msg_alerta.format(dias_para_fim, ref)

        # 3. Últimos 5 dias (diário)
        elif 1 <= dias_para_fim <= 5:
            tipo_notif = f"Diario_{dias_para_fim}"
            assunto = f"🚨 {dias_para_fim} dia(s) restantes - {ref} - {tipo_conta}"
            mensagem = msg_urgente.format(dias_para_fim)

        if tipo_notif:
            html = self.criar_card_email(
                titulo=assunto.split(" - ")[0].replace("✅ ", "").replace("⚠️ ", "").replace("🚨 ", ""),
                mensagem=mensagem,
                prestador=nome,
                referencia=ref,
                tipo_conta=tipo_conta,
                dias_restantes=dias_para_fim if dias_para_fim > 0 else None
            )

            enviado = self.enviar_email(email, assunto, html)

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
                logger.info(f"Notificação enviada: {nome} - {tipo_notif} - {ref}")
                notificacoes.append(f"{tipo_notif} → {nome} ({email})")

        return notificacoes

    def verificar_e_notificar(self):
        """Função principal: verifica todos os períodos e envia notificações pendentes"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        hoje = date.today()
        notificacoes_enviadas = []
        
        logger.info(f"Iniciando verificação de notificações - {hoje.strftime('%d/%m/%Y')}")

        try:
            # Busca prestadores ativos com datas configuradas
            cursor.execute('''
                SELECT p.id, p.nome, p.email, p.tipo_prestador,
                       d.referencia, d.faturamento_inicio, d.faturamento_fim,
                       d.recurso_inicio, d.recurso_fim
                FROM prestadores p
                JOIN datas_envio d ON p.tipo_prestador = d.tipo_prestador
                WHERE d.status = 'Ativo'
                  AND (d.faturamento_inicio IS NOT NULL OR d.recurso_inicio IS NOT NULL)
            ''')
            
            registros = cursor.fetchall()
            logger.info(f"Encontrados {len(registros)} prestadores com períodos ativos")
            
            for row in registros:
                (prest_id, nome, email, _, ref,
                 fat_ini, fat_fim, rec_ini, rec_fim) = row
                
                logger.debug(f"Processando {nome} - {ref}")
                
                # Verifica se o e-mail é válido
                if not email or not self.is_email_valido(email):
                    logger.warning(f"E-mail inválido para {nome}: {email}")
                    continue
                
                if fat_ini and fat_fim:
                    enviadas = self.processar_periodo(
                        prest_id, nome, email, ref, "Faturamento Contas",
                        fat_ini, fat_fim, hoje, cursor
                    )
                    notificacoes_enviadas.extend(enviadas)
                
                if rec_ini and rec_fim:
                    enviadas = self.processar_periodo(
                        prest_id, nome, email, ref, "Recurso de Glosas",
                        rec_ini, rec_fim, hoje, cursor
                    )
                    notificacoes_enviadas.extend(enviadas)
            
            conn.commit()
            logger.info(f"Processamento concluído. {len(notificacoes_enviadas)} notificações enviadas")

        except Exception as e:
            logger.error(f"Erro geral na verificação de notificações: {e}", exc_info=True)
            conn.rollback()

        finally:
            conn.close()

        if notificacoes_enviadas:
            logger.info(f"Notificações enviadas hoje ({len(notificacoes_enviadas)}): {', '.join(notificacoes_enviadas)}")
        else:
            logger.info("Nenhuma notificação enviada hoje")

        return notificacoes_enviadas
    
if __name__ == "__main__":
    import sys
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    # Se tiver argumento --auto, executa uma vez
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        notificador = Notificador()
        notificador.verificar_e_notificar()
    else:
        print("Use: python notificador.py --auto")