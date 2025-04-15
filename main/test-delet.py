## Versão atualizada com correções para a pasta "All Mail"

import imaplib
import os
import datetime
import concurrent.futures
import re
import chardet
import socket
import ssl
import time
from email import message_from_bytes
from email.header import decode_header
from dotenv import load_dotenv
from tqdm import tqdm
import configparser

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
ACCOUNTS = [
    {"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},
    {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
    {"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")},
    {"email": os.getenv("EMAIL_4"), "senha": os.getenv("SENHA_4")},
    {"email": os.getenv("EMAIL_6"), "senha": os.getenv("SENHA_6")},
    {"email": os.getenv("EMAIL_7"), "senha": os.getenv("SENHA_7")}
]

# Configurações de timeout e tentativas
socket.setdefaulttimeout(300)
BATCH_SIZE = 5
FETCH_TIMEOUT = 60
RETRY_DELAY = 10
MAX_RETRIES = 7

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BACKUP_DIR = "backup_emails"

# Configuração de anos para backup
try:
    config = configparser.ConfigParser()
    if not config.read('config.ini'):
        config['Settings'] = {'years': '5', 'enabled_emails': 'Email 1,Email 2,Email 3'}
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
except Exception as e:
    print(f"Erro na configuração: {e}")
    config = {'Settings': {'years': '5', 'enabled_emails': 'Email 1,Email 2,Email 3'}}

years = float(config['Settings'].get('years', '2.1'))
DATA_CORTE = (datetime.datetime.now() - datetime.timedelta(days=365*years)).strftime("%d-%b-%Y")

# Lista de pastas atualizada com tratamento especial para All Mail
PASTAS = [
    "INBOX",
    "[Gmail]/All Mail",  # Nome correto para a pasta All Mail
    "[Gmail]/Drafts",
    "[Gmail]/Important",
    "[Gmail]/Sent Mail",
    "[Gmail]/Spam",
    "[Gmail]/Starred",
    "[Gmail]/Trash",
    # Outras pastas...
]

def conectar_gmail(email, senha):
    """Estabelece conexão com o servidor IMAP do Gmail."""
    try:
        print(f"\nTentando conectar: {email}")
        if not email or not senha:
            print(f"❌ Credenciais faltando para: {email}")
            return None
            
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=FETCH_TIMEOUT)
        mail.login(email, senha)
        print(f"\n{'='*50}")
        print(f"✅ Conectado ao Gmail: {email}")
        print(f"{'='*50}")
        return mail
    except Exception as e:
        print(f"\n{'='*50}")
        print(f"❌ Erro de conexão: {email}")
        print(f"Detalhes: {e}")
        print(f"{'='*50}")
        time.sleep(RETRY_DELAY)
        return None

def limpar_pasta(mail, pasta, email):
    """Função modificada para lidar com All Mail corretamente"""
    try:
        print(f"\n[📁] Processando pasta: {pasta}")
        
        # Seleciona a pasta
        status, _ = mail.select(pasta, readonly=False)
        if status != "OK":
            print(f"[-] Não foi possível acessar a pasta '{pasta}'")
            return

        # Busca mensagens antigas
        status, data = mail.search(None, f'(BEFORE {DATA_CORTE})')
        if status != "OK":
            print(f"[-] Erro ao buscar e-mails em '{pasta}'")
            return

        email_ids = data[0].split()
        total_emails = len(email_ids)
        
        if total_emails == 0:
            print(f"[!] Nenhum e-mail encontrado em '{pasta}'")
            return

        print(f"[🔍] Encontrados {total_emails} e-mail(s) para limpar em '{pasta}'")
        
        # Processamento especial para All Mail
        if "All Mail" in pasta:
            print("[ℹ️] Modo especial para All Mail - marcando como excluído e movendo para Trash")
            
            for i in range(0, total_emails, BATCH_SIZE):
                batch = email_ids[i:i + BATCH_SIZE]
                batch_str = ','.join([id.decode() if isinstance(id, bytes) else str(id) for id in batch])
                
                try:
                    # Marca para exclusão e move para a lixeira
                    mail.store(batch_str, '+X-GM-LABELS', '\\Trash')
                    mail.store(batch_str, '+FLAGS', '\\Deleted')
                    
                    # Progresso
                    progress = (i + len(batch)) / total_emails * 100
                    print(f"\r[⏳] Progresso: {progress:.1f}%", end='', flush=True)
                    
                except Exception as e:
                    print(f"\n[-] Erro ao processar lote: {e}")
                    continue
            
            # Expurga as mensagens marcadas
            mail.expunge()
            print(f"\n[✔] Mensagens em All Mail marcadas para exclusão")
        
        else:
            # Processamento normal para outras pastas
            for i in range(0, total_emails, BATCH_SIZE):
                batch = email_ids[i:i + BATCH_SIZE]
                batch_str = ','.join([id.decode() if isinstance(id, bytes) else str(id) for id in batch])
                
                try:
                    mail.store(batch_str, '+FLAGS', '\\Deleted')
                    progress = (i + len(batch)) / total_emails * 100
                    print(f"\r[⏳] Progresso: {progress:.1f}%", end='', flush=True)
                except Exception as e:
                    print(f"\n[-] Erro ao processar lote: {e}")
                    continue
            
            mail.expunge()
            print(f"\n[✔] {total_emails} e-mail(s) excluído(s) de '{pasta}'")
            
    except Exception as e:
        print(f"\n[-] Erro geral ao limpar pasta '{pasta}': {e}")

def limpar_conta_completa(email, senha):
    """Função principal para limpeza de contas"""
    mail = conectar_gmail(email, senha)
    if not mail:
        return

    try:
        print(f"\n[🔍] Iniciando limpeza para {email}")
        
        # Primeiro processa a All Mail se existir
        if "juan.investur" in email.lower():
            print("\n[⚠️] Processando All Mail primeiro (conta especial)")
            limpar_pasta(mail, "[Gmail]/All Mail", email)
            time.sleep(5)  # Delay para garantir processamento

        # Depois processa outras pastas
        for pasta in PASTAS:
            if pasta != "[Gmail]/All Mail":  # Já processamos esta
                try:
                    limpar_pasta(mail, pasta, email)
                    time.sleep(1)  # Pequeno delay entre pastas
                except Exception as e:
                    print(f"\n[❌] Erro ao processar pasta {pasta}: {str(e)}")
                    continue

    finally:
        try:
            # Verifica se a conexão ainda está ativa
            if mail.state == 'SELECTED':
                mail.close()
            mail.logout()
            print(f"\n[🎉] Limpeza concluída para {email}!")
        except Exception as e:
            print(f"\n[⚠️] Erro ao encerrar conexão: {str(e)}")

if __name__ == "__main__":
    try:
        print("\n[ℹ️] Iniciando processo de limpeza...")
        
        # Filtra contas ativas
        enabled_emails = config['Settings'].get('enabled_emails', '').split(',')
        active_accounts = [acc for acc in ACCOUNTS 
                          if acc["email"] and acc["senha"] and
                          any(f"Email {i}" in enabled_emails 
                              for i in range(1, 8) 
                              if acc["email"] == os.getenv(f"EMAIL_{i}"))]

        print(f"Contas ativas: {[acc['email'] for acc in active_accounts]}")
        
        # Executa para cada conta
        for account in active_accounts:
            if "juan.investur" in account["email"].lower():
                print("\n[⚠️] Processando conta especial juan.investur@gmail.com")
                limpar_conta_completa(account["email"], account["senha"])
            else:
                limpar_conta_completa(account["email"], account["senha"])
                
    except KeyboardInterrupt:
        print("\n[⚠️] Interrompido pelo usuário")
    except Exception as e:
        print(f"\n[❌] Erro no processo principal: {e}")
    finally:
        print("\n[✅] Processo concluído")