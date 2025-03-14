import imaplib
import email
import os
import datetime
from email.header import decode_header

# Configuração da conta Gmail
EMAIL = "juan.investur@gmail.com"
SENHA = "ilts eais udyn fejz"  # Use a senha gerada no App Passwords
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
    """Salva o e-mail como arquivo .eml e move para a lixeira após o backup."""
    subject, encoding = decode_header(email_msg["Subject"])[0]
    if isinstance(subject, bytes) and encoding:
        subject = subject.decode(encoding)
    
    subject = str(subject) if subject else "email_sem_assunto"
    subject = "".join(c if c.isalnum() or c in " _-" else "_" for c in subject)
    filename = f"{uid}_{subject}.eml"

    # Criar pasta de backup se não existir
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    # Salva o e-mail
    with open(os.path.join(BACKUP_DIR, filename), "w", encoding="utf-8") as f:
        f.write(email_msg.as_string())

    print(f"[✔] E-mail salvo: {filename}")

def fazer_backup():
    """Baixa e-mails dos últimos 3 anos, salva e depois exclui do Gmail."""
    mail = conectar_gmail()
    if not mail:
        return

    mail.select("inbox")  # Acessa a caixa de entrada

    # Define a data de corte (3 anos atrás)
    data_corte = (datetime.datetime.now() - datetime.timedelta(days=0*365)).strftime("%d-%b-%Y")

    # Busca apenas e-mails antigos (3 anos ou mais)
    status, messages = mail.search(None, f'BEFORE {data_corte}')
    emails_ids = messages[0].split()

    if not emails_ids:
        print("[-] Nenhum e-mail encontrado para backup e exclusão.")
        return

    print(f"[+] Encontrados {len(emails_ids)} e-mails para backup e exclusão.")

    for uid in emails_ids:
        mail.noop()  # Mantém a conexão ativa
        status, msg_data = mail.fetch(uid, "(RFC822)")
        if status != "OK":
            print(f"[-] Erro ao baixar e-mail {uid.decode()}")
            continue

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                email_msg = email.message_from_bytes(response_part[1])
                salvar_email(uid.decode(), email_msg)

        # Move o e-mail para a lixeira e o apaga
        mail.store(uid, "+X-GM-LABELS", "\\Trash")  # Move para a lixeira
        mail.expunge()  # Apaga permanentemente

    mail.logout()
    print("[✔] Backup concluído! E-mails antigos excluídos.")

if __name__ == "__main__":
    fazer_backup()
