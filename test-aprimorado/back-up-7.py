# Nova versao do codigo dia 24/03/25
## Nessa nova versao irei recolher apenas os emails para back-up
### Com um limite de 500 emails para cada email 
#### Serao 6 emails para back-up sem a funsao de excluir 
import imaplib
import os
import datetime
import time
from email import message_from_bytes
from email.header import decode_header
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração das contas Gmail
ACCOUNTS = [
    {"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},
    {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
    {"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")},
]

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BACKUP_DIR = "backup_emails"
DATA_CORTE = (datetime.datetime.now() - datetime.timedelta(days=0)).strftime("%d-%b-%Y")


def conectar_gmail(email, senha):
    """Estabelece conexão com o servidor IMAP do Gmail."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email, senha)
        print(f"[+] Conectado ao Gmail: {email}")
        return mail
    except Exception as e:
        print(f"[-] Erro ao conectar: {email} - {e}")
        return None


def limpar_nome_arquivo(nome, max_length=100):
    """Sanitiza o nome do arquivo para evitar caracteres inválidos."""
    nome = "".join(c if c.isalnum() or c in " _-" else "_" for c in nome)
    return nome[:max_length]


def salvar_email(uid, email_msg, account_email):
    """Salva um e-mail no diretório de backup."""
    subject, encoding = decode_header(email_msg["Subject"])[0]

    if isinstance(subject, bytes):
        try:
            if encoding is None or encoding.lower() == "unknown-8bit":
                encoding = "utf-8"
            subject = subject.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            subject = subject.decode("latin-1", errors="ignore")

    subject = subject.strip() if subject else "email_sem_assunto"
    subject = limpar_nome_arquivo(subject)

    account_folder = os.path.join(BACKUP_DIR, account_email)
    os.makedirs(account_folder, exist_ok=True)
    filename = os.path.join(account_folder, f"{uid}_{subject}.eml")

    with open(filename, "w", encoding="utf-8", errors="ignore") as f:
        f.write(email_msg.as_string())

    print(f"[✔] E-mail salvo: {filename}")
    return True


def excluir_email(uid, mail):
    """Exclui um e-mail do Gmail após o backup."""
    try:
        mail.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
        print(f"[🗑] E-mail UID {uid} marcado para exclusão.")
    except Exception as e:
        print(f"[-] Erro ao excluir e-mail UID {uid}: {e}")


def fazer_backup(email, senha):
    """Realiza o backup dos e-mails antigos de uma conta e os exclui do servidor."""
    mail = conectar_gmail(email, senha)
    if not mail:
        return

    mail.select("inbox")
    status, messages = mail.uid("SEARCH", None, f'BEFORE {DATA_CORTE}')
    if status != "OK":
        print(f"[-] Erro ao buscar e-mails em {email}")
        mail.logout()
        return

    emails_ids = messages[0].split()
    if not emails_ids:
        print(f"[-] Nenhum e-mail antigo encontrado para backup em {email}.")
        mail.logout()
        return

    total_emails = len(emails_ids)
    print(f"[+] Processando {total_emails} e-mails para backup e exclusão em {email}.")

    for i, uid in enumerate(emails_ids, start=1):
        uid = uid.decode()
        status, msg_data = mail.uid("FETCH", uid, "(RFC822)")
        if status != "OK":
            continue

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                email_msg = message_from_bytes(response_part[1])
                if salvar_email(uid, email_msg, email):
                    excluir_email(uid, mail)

        mail.expunge()
        progresso = (i / total_emails) * 100
        print(f"[⏳] Progresso: {progresso:.2f}%")
        time.sleep(0.5)

    mail.logout()
    print(f"[✔] Backup e exclusão concluídos para {email}!")


if __name__ == "__main__":
    for account in ACCOUNTS:
        if account["email"] and account["senha"]:
            fazer_backup(account["email"], account["senha"])
