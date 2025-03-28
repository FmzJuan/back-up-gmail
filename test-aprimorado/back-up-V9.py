import imaplib
import os
import time
import concurrent.futures
import sys
import signal
from email import message_from_bytes
from email.header import decode_header
from dotenv import load_dotenv
import humanize
from datetime import datetime, timedelta

# Configurações iniciais
load_dotenv()

# Constantes
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BACKUP_DIR = "backup_emails"
YEARS_BACK = 3  # Quantidade de anos para buscar e-mails

# Definir a data de três anos atrás para busca
DATA_LIMITE = (datetime.now() - timedelta(days=365 * 0)).strftime("%d-%b-%Y")

# Contas de e-mail
ACCOUNTS = [
    {"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},
    {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
]

MAX_THREADS = min(3, len(ACCOUNTS))
interrupted = False

def signal_handler(sig, frame):
    """Captura o sinal de interrupção (Ctrl+C)"""
    global interrupted
    print("\n\n[!] Recebido comando para interromper... Aguarde finalização segura")
    interrupted = True

signal.signal(signal.SIGINT, signal_handler)

def conectar_gmail(email, senha):
    """Estabelece conexão segura com o servidor IMAP"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=15)
        mail.login(email, senha)
        return mail
    except Exception as e:
        print(f"[-] Erro ao conectar {email}: {e}")
        return None

def listar_pastas(mail):
    """Lista as pastas de interesse na conta de e-mail"""
    try:
        status, pastas = mail.list()
        return [p.decode() for p in pastas if "INBOX" in p.decode()] if status == "OK" else []
    except Exception as e:
        print(f"[-] Erro ao listar pastas: {e}")
        return []

def criar_pastas_backup(email, pastas):
    """Cria a estrutura de diretórios para armazenar e-mails"""
    base_dir = os.path.join(BACKUP_DIR, email.split('@')[0])
    for pasta in pastas:
        os.makedirs(os.path.join(base_dir, *pasta.replace("[Gmail]/", "").split('/')), exist_ok=True)
    return base_dir

def salvar_email(uid, msg, caminho):
    """Salva o e-mail no formato .eml"""
    try:
        assunto = decode_header(msg["Subject"] or "Sem Assunto")[0]
        assunto = assunto[0].decode(assunto[1] or 'utf-8', errors='replace') if isinstance(assunto[0], bytes) else str(assunto[0])
        assunto = "".join(c if c.isalnum() or c in " _-." else "_" for c in assunto)[:50]
        data = "".join(c if c.isalnum() else "_" for c in (msg.get("Date", "")[:25]))
        filename = os.path.join(caminho, f"{data}_{assunto}_{uid}.eml")

        with open(filename, "wb") as f:
            f.write(msg.as_bytes())

        return True, os.path.getsize(filename)
    except Exception as e:
        print(f"[-] Erro ao salvar e-mail {uid}: {e}")
        return False, 0

def processar_pasta(mail, pasta, account_dir):
    """Processa e salva e-mails de uma pasta"""
    global interrupted
    print(f"\n[📁] Processando pasta: {pasta}")
    mail.select(f'"{pasta}"' if ' ' in pasta else pasta)
    status, messages = mail.uid("SEARCH", None, f'(SINCE "{DATA_LIMITE}")')

    if status != "OK" or not messages[0]:
        print(f"[⚠] Nenhum e-mail encontrado em {pasta}")
        return 0, 0

    email_uids = messages[0].split()
    caminho_pasta = os.path.join(account_dir, *pasta.replace("[Gmail]/", "").split('/'))
    total_salvos, total_tamanho = 0, 0

    # Paralelismo no processamento de e-mails dentro da pasta
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futuros = {executor.submit(processar_email, mail, uid, caminho_pasta): uid for uid in email_uids}

        for i, futuro in enumerate(concurrent.futures.as_completed(futuros), start=1):
            if interrupted:
                break
            sucesso, tamanho = futuro.result()
            if sucesso:
                total_salvos += 1
                total_tamanho += tamanho
                print(f"[💾] Progresso: [{('=' * (i * 20 // len(email_uids))).ljust(20)}] {i}/{len(email_uids)} e-mails da pasta {pasta}", end="\r")

    print(f"\n[✔] Concluído: {total_salvos} e-mails salvos ({humanize.naturalsize(total_tamanho)}) na pasta {pasta}")
    return total_salvos, total_tamanho

def processar_email(mail, uid, caminho_pasta):
    """Faz o fetch e salva um único e-mail"""
    try:
        status, data = mail.uid("FETCH", uid.decode(), "(RFC822)")
        if status == "OK" and isinstance(data[0], tuple):
            return salvar_email(uid.decode(), message_from_bytes(data[0][1]), caminho_pasta)
    except Exception as e:
        print(f"[-] Erro ao processar e-mail {uid}: {e}")
    return False, 0

def fazer_backup(email, senha):
    """Executa o backup de todas as pastas de uma conta"""
    global interrupted
    mail = conectar_gmail(email, senha)
    if not mail:
        return
    pastas = listar_pastas(mail)
    if not pastas:
        return
    account_dir = criar_pastas_backup(email, pastas)
    total_emails, total_tamanho = 0, 0

    # Processamento paralelo das pastas mantendo a progressão
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futuros = {executor.submit(processar_pasta, mail, pasta, account_dir): pasta for pasta in pastas}

        for futuro in concurrent.futures.as_completed(futuros):
            if interrupted:
                break
            salvos, tamanho = futuro.result()
            total_emails += salvos
            total_tamanho += tamanho

    print(f"\n[✔] Backup concluído para {email}: {total_emails} e-mails ({humanize.naturalsize(total_tamanho)})")
    mail.logout()

if __name__ == "__main__":
    print("\n[❗] Pressione Ctrl+C para interromper o backup")

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = [executor.submit(fazer_backup, acc["email"], acc["senha"]) for acc in ACCOUNTS if acc["email"] and acc["senha"]]
            concurrent.futures.wait(futures)
        print("\n[✔✔✔] Todos os backups concluídos com sucesso!")
    except KeyboardInterrupt:
        interrupted = True
        print("\n[!] Interrompendo backups...")
