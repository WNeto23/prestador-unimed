import schedule
import time
from notificador import Notificador
import logging
import sys
import os

# Detecta BASE_DIR (funciona tanto no .exe quanto como script)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configura logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'notificacoes.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def job():
    """Função que será executada diariamente"""
    logging.info("Iniciando verificação de notificações...")
    
    try:
        notificador = Notificador()
        notificacoes = notificador.verificar_e_notificar()
        
        if notificacoes:
            logging.info(f"Enviadas {len(notificacoes)} notificações:")
            for nome, email, tipo in notificacoes:
                logging.info(f"  - {nome} ({email}): {tipo}")
        else:
            logging.info("Nenhuma notificação necessária hoje.")
            
    except Exception as e:
        logging.error(f"Erro durante execução: {e}")

def main():
    """Configura e inicia o agendador"""
    logging.info("Sistema de notificações iniciado (NeonDB)")
    logging.info("Agendado para executar todos os dias às 08:00")
    
    # Agenda para executar todos os dias às 08:00
    schedule.every().day.at("08:00").do(job)
    
    # Executa uma vez imediatamente para teste
    logging.info("Executando verificação inicial...")
    job()
    
    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verifica a cada minuto

if __name__ == "__main__":
    main()