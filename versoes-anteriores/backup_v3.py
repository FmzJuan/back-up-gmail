import imaplib
import email
import os
import datetime
from email.header import decode_header
import re

# Configuração da conta Gmail
EMAIL = "jmenega3@gmail.com"
SENHA = "ojlo xpqn rggl rhhz"  # Use a senha gerada no App Passwords
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BACKUP_DIR = "backup_emails"

def conectar_gmail():
    """Conecta ao servidor IMAP do Gmail."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL, SENHA)
        print(f"[+] Conectado ao Gmail com sucesso. no email :{EMAIL}")
        return mail
    except Exception as e:
        print("[-] Erro ao conectar:", e)
        return None

# Função para limpar caracteres inválidos e limitar tamanho do nome do arquivo
def limpar_nome_arquivo(nome):
    nome_limpo = re.sub(r'[<>:"/\\|?*]', '_', nome)  # Substitui caracteres inválidos por "_"
    return nome_limpo[:100]  # Limita o nome do arquivo a 100 caracteres

def salvar_email(uid, email_msg):
    """Salva o e-mail como arquivo .eml e marca para exclusão."""
    
    # Decodificar o assunto corretamente
    subject, encoding = decode_header(email_msg["Subject"])[0]
    if isinstance(subject, bytes):
        try:
            subject = subject.decode(encoding if encoding else "utf-8")
        except (UnicodeDecodeError, TypeError):
            subject = subject.decode("latin-1", errors="ignore")  # Evita erro de decodificação

    subject = subject.strip() if subject else "email_sem_assunto"
    subject = limpar_nome_arquivo(subject)  # Aplica limpeza

    filename = f"{uid}_{subject}.eml"

    # Criar pasta de backup se não existir
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    caminho_arquivo = os.path.join(BACKUP_DIR, filename)

    try:
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            f.write(email_msg.as_string())
        print(f"[✔] E-mail salvo: {filename}")
    except Exception as e:
        print(f"❌ Erro ao salvar o e-mail {filename}: {e}")

def fazer_backup():
    """Baixa e-mails dos últimos 2 anos, salva e exclui permanentemente do Gmail."""
    mail = conectar_gmail()
    if not mail:
        return

    mail.select("inbox")  # Acessa a caixa de entrada

    # Define a data de corte (2 anos atrás)
    data_corte = (datetime.datetime.now() - datetime.timedelta(days=1*365)).strftime("%d-%b-%Y")

    # Busca apenas e-mails antigos (2 anos ou mais)
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

        # Marca para exclusão
        mail.store(uid, "+FLAGS", "\\Deleted")

    # Apaga permanentemente os e-mails marcados
    mail.expunge()

    mail.logout()
    print("[✔] Backup concluído! E-mails antigos excluídos permanentemente.")

if __name__ == "__main__":
    fazer_backup()