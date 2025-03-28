##atualizei para ele pegar retomar a contagem na pasta save de back-up
import imaplib
import os
import datetime
from email import message_from_bytes
from email.header import decode_header

# Configuração das contas Gmail
ACCOUNTS = [
    {"email": "juanmeneghesso2@gmail.com", "senha": "airx bdwl owoa iflk"},
    {"email": "juan.investur@gmail.com", "senha": "ilts eais udyn fejz"},
    {"email": "jmenega3@gmail.com", "senha": "ojlo xpqn rggl rhhz"}
]

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BACKUP_DIR = "backup_emails"
DATA_CORTE = (datetime.datetime.now() - datetime.timedelta(days=0*365)).strftime("%d-%b-%Y")


def conectar_gmail(email, senha):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email, senha)
        print(f"[+] Conectado ao Gmail com sucesso: {email}")
        return mail
    except Exception as e:
        print(f"[-] Erro ao conectar em {email}: {e}")
        return None


def verificar_conexao(mail):
    try:
        mail.noop()
        return True
    except:
        return False


def limpar_nome_arquivo(nome, max_length=100):
    nome = "".join(c if c.isalnum() or c in " _-" else "_" for c in nome)
    return nome[:max_length]


def obter_ultimo_uid_salvo(account_email):
    account_folder = os.path.join(BACKUP_DIR, account_email)
    if not os.path.exists(account_folder):
        return None
    arquivos = sorted(os.listdir(account_folder))
    if not arquivos:
        return None
    
    ultimo_arquivo = arquivos[-1]
    partes = ultimo_arquivo.split("_")
    if partes[0].isdigit():
        return int(partes[0])
    return None


def salvar_email(uid, email_msg, account_email):
    subject, encoding = decode_header(email_msg["Subject"])[0]
    if isinstance(subject, bytes):
        try:
            subject = subject.decode(encoding if encoding else "utf-8")
        except (UnicodeDecodeError, TypeError):
            subject = subject.decode("latin-1", errors="ignore")
    
    subject = subject.strip() if subject else "email_sem_assunto"
    subject = limpar_nome_arquivo(subject)
    
    account_folder = os.path.join(BACKUP_DIR, account_email)
    os.makedirs(account_folder, exist_ok=True)
    
    filename = os.path.join(account_folder, f"{uid}_{subject}.eml")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(email_msg.as_string())
    
    print(f"[✔] E-mail salvo ({account_email}): {filename}")


def fazer_backup(email, senha):
    mail = conectar_gmail(email, senha)
    if not mail:
        return
    
    mail.select("inbox")
    status, messages = mail.search(None, f'BEFORE {DATA_CORTE}')
    if status != "OK":
        print(f"[-] Erro ao buscar e-mails em {email}")
        mail.logout()
        return
    
    emails_ids = messages[0].split()
    if not emails_ids:
        print(f"[-] Nenhum e-mail antigo encontrado para backup em {email}.")
        return
    
    ultimo_uid = obter_ultimo_uid_salvo(email)
    emails_ids = [uid for uid in emails_ids if int(uid) > (ultimo_uid or 0)]
    emails_ids = emails_ids[:500]
    
    print(f"[+] Processando {len(emails_ids)} e-mails para backup e exclusão em {email}.")
    
    for uid in emails_ids:
        if not verificar_conexao(mail):
            print("[-] Conexão perdida, tentando reconectar...")
            mail = conectar_gmail(email, senha)
            if not mail:
                return
            mail.select("inbox")
        
        status, msg_data = mail.fetch(uid, "(RFC822)")
        if status != "OK":
            print(f"[-] Erro ao baixar e-mail {uid} em {email}")
            continue
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                email_msg = message_from_bytes(response_part[1])
                salvar_email(uid, email_msg, email)
        
        try:
            mail.store(uid, "+FLAGS", "\\Deleted")
            print(f"[✔] E-mail {uid} marcado para exclusão.")
        except Exception as e:
            print(f"[-] Erro ao marcar e-mail {uid} para exclusão: {e}")
    
    try:
        mail.expunge()
        print(f"[✔] Todos os e-mails antigos foram apagados permanentemente.")
    except Exception as e:
        print(f"[-] Erro ao tentar excluir permanentemente os e-mails: {e}")
    
    mail.logout()
    print(f"[✔] Backup concluído para {email}! E-mails antigos excluídos permanentemente.")


if __name__ == "__main__":
    for account in ACCOUNTS:
        fazer_backup(account["email"], account["senha"])
