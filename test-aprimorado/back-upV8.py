import imaplib
import os
import time
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

ACCOUNTS = [
    {"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},
    {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
    {"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")},
]

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

PASTAS_IMPORTANTES = [
    "INBOX",
    "[Gmail]/Sent Mail",
    "[Gmail]/Drafts",
    "[Gmail]/Spam",
    "[Gmail]/Trash",
    "[Gmail]/All Mail"
]

def conectar_gmail(email, senha):
    """Conecta ao servidor IMAP do Gmail e retorna o objeto de conexão."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email, senha)
        return mail
    except Exception as e:
        print(f"[-] Erro ao conectar em {email}: {e}")
        return None

def limpar_pasta(mail, pasta):
    """Apaga todos os e-mails de uma pasta e confirma a exclusão."""
    status, _ = mail.select(pasta)
    
    if status != "OK":
        print(f"[-] Falha ao acessar '{pasta}'. Pulando...")
        return

    status, messages = mail.search(None, "ALL")  # Seleciona todos os e-mails
    if status != "OK" or not messages[0]:
        print(f"[!] Nenhum e-mail encontrado em '{pasta}'.")
        return

    uids = messages[0].split()
    total = len(uids)
    print(f"[+] Apagando {total} e-mails de '{pasta}'...")

    mail.store("1:*", "+FLAGS", "\\Deleted")  # Marca como deletado
    mail.expunge()  # Remove permanentemente

    print(f"✔ E-mails apagados de '{pasta}'.")

def limpar_conta(email, senha):
    """Limpa TODAS as pastas da conta do Gmail."""
    mail = conectar_gmail(email, senha)
    if not mail:
        return

    try:
        print(f"[🔍] Limpando conta {email}...")

        # Limpar todas as pastas importantes
        for pasta in PASTAS_IMPORTANTES:
            limpar_pasta(mail, pasta)

    finally:
        mail.logout()
        print(f"[✔] Limpeza concluída para {email}!\n")

if __name__ == "__main__":
    for acc in ACCOUNTS:
        if acc["email"] and acc["senha"]:
            limpar_conta(acc["email"], acc["senha"])
