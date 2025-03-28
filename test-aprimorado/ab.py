import imaplib
import os
import datetime
import concurrent.futures
import sys
from email import message_from_bytes
from email.header import decode_header
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

ACCOUNTS = [
    {"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},
  #  {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
   # {"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")},
]

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BACKUP_DIR = "backup_emails"
DATA_CORTE = (datetime.datetime.now() - datetime.timedelta(days=0)).strftime("%d-%b-%Y")  # 2 anos
MAX_THREADS = min(3, len(ACCOUNTS))  # Máximo de 3 threads simultâneas
PASTAS = ["inbox", "[Gmail]/Promotions", "[Gmail]/Social", "[Gmail]/Updates"]
LIXEIRA = "[Gmail]/Trash"  # Caminho correto da lixeira
PROGRESS_BAR = "/..|....\\"


def conectar_gmail(email, senha):
    """Estabelece conexão com o servidor IMAP do Gmail com timeout."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=10)
        mail.login(email, senha)
        print(f"\n[+] Conectado ao Gmail: {email}")
        return mail
    except imaplib.IMAP4.abort:
        print(f"[-] Timeout ao conectar: {email}")
    except Exception as e:
        print(f"[-] Erro ao conectar: {email} - {e}")
    return None


def salvar_email(uid, email_msg, account_email, pasta):
    """Salva um e-mail no diretório de backup."""
    subject, encoding = decode_header(email_msg["Subject"])[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8", errors="ignore")
    subject = subject.strip() if subject else "email_sem_assunto"
    subject = "".join(c if c.isalnum() or c in " _-" else "_" for c in subject)[:100]

    account_folder = os.path.join(BACKUP_DIR, account_email, pasta.replace("[Gmail]/", ""))
    os.makedirs(account_folder, exist_ok=True)
    filename = os.path.join(account_folder, f"{uid}_{subject}.eml")

    with open(filename, "w", encoding="utf-8", errors="ignore") as f:
        f.write(email_msg.as_string())


def mover_para_lixeira(uids, mail):
    """Move e-mails para a Lixeira do Gmail para garantir exclusão."""
    if uids:
        uids_str = ",".join(uids)
        status, _ = mail.uid("MOVE", uids_str, LIXEIRA)
        if status == "OK":
            print(f"[🗑] {len(uids)} e-mails movidos para a Lixeira.")
            mail.expunge()  # Confirma a exclusão
        else:
            print(f"[-] Erro ao mover e-mails para a Lixeira.")


def mostrar_progresso(atual, total):
    """Exibe a barra de progresso animada."""
    progresso = int((atual / total) * 7)  # A barra tem 7 posições
    barra = PROGRESS_BAR[progresso]  # Escolhe o caractere correspondente
    sys.stdout.write(f"\r[{barra}] Processando {atual}/{total} e-mails... ")
    sys.stdout.flush()


def fazer_backup(email, senha):
    """Realiza o backup e exclusão de e-mails antigos de todas as pastas relevantes."""
    mail = conectar_gmail(email, senha)
    if not mail:
        return

    try:
        for pasta in PASTAS:
            status, _ = mail.select(pasta)
            if status != "OK":
                print(f"\n[-] Não foi possível acessar a pasta {pasta} em {email}. Pulando...")
                continue

            status, messages = mail.uid("SEARCH", None, f'BEFORE {DATA_CORTE}')
            if status != "OK":
                print(f"\n[-] Erro ao buscar e-mails em {pasta} ({email})")
                continue

            emails_ids = messages[0].split()
            total_emails = len(emails_ids)
            if total_emails == 0:
                print(f"\n[-] Nenhum e-mail antigo encontrado em {pasta} ({email}).")
                continue

            print(f"\n[+] {total_emails} e-mails serão processados em {pasta} ({email}).")

            batch_size = 10
            uids_to_delete = []

            for i in range(0, total_emails, batch_size):
                batch_uids = emails_ids[i : i + batch_size]
                uids_str = ",".join(uid.decode() for uid in batch_uids)

                status, msg_data = mail.uid("FETCH", uids_str, "(RFC822)")
                if status != "OK":
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        uid = response_part[0].split()[0].decode()
                        email_msg = message_from_bytes(response_part[1])
                        salvar_email(uid, email_msg, email, pasta)
                        uids_to_delete.append(uid)

                mostrar_progresso(i + len(batch_uids), total_emails)

            mover_para_lixeira(uids_to_delete, mail)
            print("\n[✔] Backup e exclusão concluídos para", pasta)

    finally:
        mail.logout()
        print(f"\n[✔] Backup finalizado para {email}!")


if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [executor.submit(fazer_backup, acc["email"], acc["senha"]) for acc in ACCOUNTS if acc["email"] and acc["senha"]]
        concurrent.futures.wait(futures, timeout=300)  # Aumentado o timeout para 5 minutos
