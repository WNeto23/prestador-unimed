import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

remetente = os.getenv("EMAIL_USER")
senha = os.getenv("EMAIL_PASS")
destinatario = "netovaltuirorv23@gmail.com"  # mude para o seu mesmo e-mail

msg = MIMEMultipart()
msg['From'] = remetente
msg['To'] = destinatario
msg['Subject'] = "Teste Unimed RV - Funcionando?"

msg.attach(MIMEText("Se você recebeu isso, o envio está funcionando!", 'plain'))

try:
    if "@gmail.com" in remetente.lower():
        server = smtplib.SMTP('smtp.gmail.com', 587)
    else:
        server = smtplib.SMTP('smtp.office365.com', 587)
    
    server.starttls()
    server.login(remetente, senha)
    server.send_message(msg)
    server.quit()
    print("✅ E-mail de teste enviado com sucesso!")
except Exception as e:
    print(f"❌ Erro: {e}")