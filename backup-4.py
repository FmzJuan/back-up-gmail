import imaplib
import os
import time
from email import message_from_bytes
from email.header import decode_header

# Configuração das contas Gmail
ACCOUNTS = [
    {"email": "juanmeneghesso2@gmail.com", "senha": "airx bdwl owoa iflk"},
    {"email": "jmenega3@gmail.com", "senha": "ojlo xpqn rggl rhhz"},
    {"email": "juan.investur@gmail.com", "senha": "ilts eais udyn fejz"}
]

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BACKUP_DIR = "backup_emails"
EMAILS_POR_CONTA = 10  # Número máximo de e-mails para backup por conta

def conectar_gmail(email, senha):
    """Conecta ao servidor IMAP do Gmail."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email, senha)
        print(f"[+] Conectado ao Gmail com sucesso: {email}")
        return mail
    except Exception as e:
        print(f"[-] Erro ao conectar em {email}: {e}")
        return None

def verificar_conexao(mail):
    """Verifica se a conexão com o Gmail ainda está ativa."""
    try:
        mail.noop()
        return True
    except:
        return False

def salvar_email(uid, email_msg, account_email):
    """Salva o e-mail como arquivo .eml."""
    subject, encoding = decode_header(email_msg["Subject"])[0]
    if isinstance(subject, bytes):
        try:
            subject = subject.decode(encoding if encoding else "utf-8")
        except (UnicodeDecodeError, TypeError):
            subject = subject.decode("latin-1", errors="ignore")

    subject = subject.strip() if subject else "email_sem_assunto"
    subject = "".join(c if c.isalnum() or c in " _-" else "_" for c in subject)
    account_folder = os.path.join(BACKUP_DIR, account_email)
    os.makedirs(account_folder, exist_ok=True)
    filename = os.path.join(account_folder, f"{uid}_{subject}.eml")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(email_msg.as_string())
    
    print(f"[✔] E-mail salvo ({account_email}): {filename}")

def fazer_backup(email, senha):
    """Baixa um número limitado de e-mails, salva e exclui permanentemente do Gmail."""
    mail = conectar_gmail(email, senha)
    if not mail:
        return
    
    mail.select("inbox")
    
    # Pega TODOS os e-mails da caixa de entrada
    status, messages = mail.search(None, "ALL")  

    if status != "OK":
        print(f"[-] Erro ao buscar e-mails em {email}")
        mail.logout()
        return

    emails_ids = messages[0].split()
    
    if not emails_ids:
        print(f"[-] Nenhum e-mail encontrado para backup em {email}.")
    else:
        emails_ids = emails_ids[:EMAILS_POR_CONTA]  # Limita a 10 e-mails
        print(f"[+] Processando {len(emails_ids)} e-mails para backup e exclusão permanente em {email}.")
        
        for uid in emails_ids:
            time.sleep(2)  # Evita bloqueios do Gmail
            uid = uid.decode() if isinstance(uid, bytes) else str(uid)
            
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
            
            # Excluindo permanentemente os e-mails
            try:
                mail.store(uid, "+FLAGS", "\\Deleted")
                print(f"[✔] E-mail {uid} marcado para exclusão.")
            except Exception as e:
                print(f"[-] Erro ao marcar e-mail {uid} para exclusão: {e}")

        # Expunge para deletar de vez os e-mails
        try:
            mail.expunge()
            print(f"[✔] Todos os e-mails processados foram apagados permanentemente.")
        except Exception as e:
            print(f"[-] Erro ao tentar excluir permanentemente os e-mails: {e}")
    
    mail.logout()
    print(f"[✔] Backup concluído para {email}! E-mails antigos excluídos permanentemente.")

if __name__ == "__main__":
    for account in ACCOUNTS:
        fazer_backup(account["email"], account["senha"])
