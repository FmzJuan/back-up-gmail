import imaplib
import email
import os
from email.header import decode_header

# Configuração da conta Gmail
EMAIL = "juan.investur@gmail.com"
SENHA = "ilts eais udyn fejz"   # Use a senha gerada no App Passwords
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BACKUP_DIR = "backup_emails"

def conectar_gmail():
    """Conecta ao servidor IMAP do Gmail."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL, SENHA)
        print("[+] Conectado ao Gmail com sucesso.")
        return mail
    except Exception as e:
        print("[-] Erro ao conectar:", e)
        return None

def salvar_email(uid, email_msg):
    """Salva o e-mail como arquivo .eml."""
    subject, encoding = decode_header(email_msg["Subject"])[0]
    if isinstance(subject, bytes) and encoding:
        subject = subject.decode(encoding)
    
    # Evita caracteres inválidos no nome do arquivo
    subject = str(subject)  # Garante que seja string
    subject = "".join(c if c.isalnum() or c in " _-" else "_" for c in subject)
    filename = f"{uid}_{subject}.eml"

    # Salva o e-mail em formato EML
    with open(os.path.join(BACKUP_DIR, filename), "w", encoding="utf-8") as f:
        f.write(email_msg.as_string())

    print(f"[✔] E-mail salvo: {filename}")

def fazer_backup():
    """Baixa e-mails e os salva localmente."""
    mail = conectar_gmail()
    if not mail:
        return

    mail.select("inbox")  # Acessa a caixa de entrada
    status, messages = mail.search(None, "ALL")  # Busca todos os e-mails
    emails_ids = messages[0].split()

    if not emails_ids:
        print("[-] Nenhum e-mail encontrado.")
        return

    print(f"[+] Encontrados {len(emails_ids)} e-mails para backup.")

    # Criar pasta de backup se não existir
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    for uid in emails_ids:
        status, msg_data = mail.fetch(uid, "(RFC822)")
        if status != "OK":
            print(f"[-] Erro ao baixar e-mail {uid.decode()}")
            continue

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                email_msg = email.message_from_bytes(response_part[1])
                salvar_email(uid.decode(), email_msg)

    mail.logout()
    print("[✔] Backup concluído!")

if __name__ == "__main__":
    fazer_backup()
