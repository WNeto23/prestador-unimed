"""
Teste de envio de e-mail usando o notificador e template reais.
Substitui dados do banco por dados fictícios para validar visual e entrega.
"""
from datetime import date
from notificador import Notificador

# ====================== DADOS DE TESTE ======================
DESTINATARIO = "netovaltuirorv23@gmail.com"  # <- altere se quiser

prestador_teste = {
    "id": 0,
    "nome": "Dr. Teste Silva",
    "email": DESTINATARIO,
    "referencia": "Março/2026",
    "tipo_conta": "Faturamento Contas",
    "fat_ini": date(2026, 3, 1),
    "fat_fim": date(2026, 3, 31),
    "guias": [
        date(2026, 3, 2),
        date(2026, 3, 10),
        date(2026, 3, 20),
        date(2026, 3, 27),
    ]
}

# ====================== EXECUÇÃO ======================
print("🚀 Iniciando teste de e-mail...\n")

notificador = Notificador()

if not notificador.email_login:
    print("❌ EMAIL_LOGIN não encontrado no .env — verifique as variáveis de ambiente.")
    exit(1)

print(f"📧 Remetente : {notificador.email_remetente}")
print(f"📬 Destinatário: {DESTINATARIO}")
print(f"🖼️  Logo URL   : {notificador.logo_url}\n")

# Gera HTML com dados fictícios
hoje = date.today()
data_fim = prestador_teste["fat_fim"]
dias_restantes = (data_fim - hoje).days

html = notificador.criar_card_email(
    titulo=f"Faturamento de Contas — {prestador_teste['referencia']}",
    mensagem=(
        f"Prezado(a) <strong>{prestador_teste['nome']}</strong>,<br><br>"
        f"Este é um <strong>e-mail de teste</strong> do sistema de notificações Unimed RV.<br>"
        f"O período de faturamento de contas referente a <strong>{prestador_teste['referencia']}</strong> "
        f"encerra em <strong>{data_fim.strftime('%d/%m/%Y')}</strong>.<br><br>"
        f"Por favor, realize o envio dentro do prazo."
    ),
    prestador=prestador_teste["nome"],
    referencia=prestador_teste["referencia"],
    tipo_conta=prestador_teste["tipo_conta"],
    data_fim=data_fim,
    dias_restantes=dias_restantes,
    guias_fisicas=prestador_teste["guias"]
)

# Envia
assunto = f"[TESTE] Notificação Unimed RV — {prestador_teste['referencia']}"
sucesso = notificador.enviar_email(
    destinatario=DESTINATARIO,
    assunto=assunto,
    html_content=html,
    data_fim=data_fim,
    tipo_conta=prestador_teste["tipo_conta"],
    prestador=prestador_teste["nome"],
    dias_restantes=dias_restantes
)

print()
if sucesso:
    print("✅ E-mail de teste enviado com sucesso!")
    print(f"   Verifique a caixa de entrada de: {DESTINATARIO}")
else:
    print("❌ Falha no envio — verifique os logs acima.")