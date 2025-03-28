import imaplib
import os
import datetime
import concurrent.futures
from email import message_from_bytes
from email.header import decode_header
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

ACCOUNTS = [
    {"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},
   # {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
    #{"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")},
]

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BACKUP_DIR = "backup_emails"
DATA_CORTE = (datetime.datetime.now() - datetime.timedelta(days=-1)).strftime("%d-%b-%Y")  # 2 anos
MAX_THREADS = min(3, len(ACCOUNTS))  # Limita para no máximo 3 threads


def conectar_gmail(email, senha):
    """Estabelece conexão com o servidor IMAP do Gmail com timeout."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=10)  # Timeout de 10s
        mail.login(email, senha)
        print(f"[+] Conectado ao Gmail: {email}")
        return mail
    except imaplib.IMAP4.abort:
        print(f"[-] Timeout ao conectar: {email}")
    except Exception as e:
        print(f"[-] Erro ao conectar: {email} - {e}")
    return None


def salvar_email(uid, email_msg, account_email):
    """Salva um e-mail no diretório de backup."""
    subject, encoding = decode_header(email_msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8", errors="ignore")
    subject = subject.strip() if subject else "email_sem_assunto"
    subject = "".join(c if c.isalnum() or c in " _-" else "_" for c in subject)[:100]

    account_folder = os.path.join(BACKUP_DIR, account_email)
    os.makedirs(account_folder, exist_ok=True)
    filename = os.path.join(account_folder, f"{uid}_{subject}.eml")

    with open(filename, "w", encoding="utf-8", errors="ignore") as f:
        f.write(email_msg.as_string())

    print(f"[✔] E-mail salvo: {filename}")


def excluir_emails(uids, mail):
    """Exclui múltiplos e-mails de uma vez e executa expunge."""
    if uids:
        mail.uid("STORE", ",".join(uids), "+FLAGS", "(\\Deleted)")
        mail.expunge()
        print(f"[🗑] {len(uids)} e-mails excluídos.")


def fazer_backup(email, senha):
    """Realiza o backup e exclusão de e-mails antigos."""
    mail = conectar_gmail(email, senha)
    if not mail:
        return

    try:
        mail.select("inbox")
        status, messages = mail.uid("SEARCH", None, f'BEFORE {DATA_CORTE}')
        if status != "OK":
            print(f"[-] Erro ao buscar e-mails em {email}")
            return

        emails_ids = messages[0].split()
        if not emails_ids:
            print(f"[-] Nenhum e-mail antigo encontrado para backup em {email}.")
            return

        print(f"[+] {len(emails_ids)} e-mails serão processados para backup e exclusão em {email}.")
        batch_size = 10
        uids_to_delete = []

        for i in range(0, len(emails_ids), batch_size):
            batch_uids = emails_ids[i : i + batch_size]
            uids_str = ",".join(uid.decode() for uid in batch_uids)

            status, msg_data = mail.uid("FETCH", uids_str, "(RFC822)")
            if status != "OK":
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    uid = response_part[0].split()[0].decode()
                    email_msg = message_from_bytes(response_part[1])
                    salvar_email(uid, email_msg, email)
                    uids_to_delete.append(uid)

        excluir_emails(uids_to_delete, mail)

    finally:
        mail.logout()
        print(f"[✔] Backup finalizado para {email}!")


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [executor.submit(fazer_backup, acc["email"], acc["senha"]) for acc in ACCOUNTS if acc["email"] and acc["senha"]]
        concurrent.futures.wait(futures, timeout=60)  # Timeout para evitar travamentos
