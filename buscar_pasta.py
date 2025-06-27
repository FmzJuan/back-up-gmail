import imaplib
import os
import imaplib
import email
import sys
from dotenv import load_dotenv


# Carrega variáveis do .env
load_dotenv()

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

ACCOUNTS = [
    #{"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")}, # meneghesso2
    #{"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")}, # juan invt
    #{"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")}, # jmenega3
    #{"email": os.getenv("EMAIL_4"), "senha": os.getenv("SENHA_4")}, # anderson
    {"email": os.getenv("EMAIL_5"), "senha": os.getenv("SENHA_5")}, # silvia
    #{"email": os.getenv("EMAIL_6"), "senha": os.getenv("SENHA_6")}, # priscila test
    #{"email": os.getenv("EMAIL_7"), "senha": os.getenv("SENHA_7")}, # amanda test
    #{"email": os.getenv("EMAIL_8"), "senha": os.getenv("SENHA_8")},# marcel pessoal
    #{"email": os.getenv("EMAIL_9"), "senha": os.getenv("SENHA_9")},# marcel invt
    # Adicione mais contas se necessário
]

def conectar_gmail(email, senha):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email, senha)
        return mail
    except Exception as e:
        print(f"❌ Erro ao conectar com {email}: {e}")
        return None

def decodificar_nome_pasta(nome_bruto):
    try:
        # O nome da pasta geralmente vem entre aspas no final da linha
        partes = nome_bruto.decode().split(' "/" ')
        if len(partes) == 2:
            return partes[1].encode().decode('utf-7')
        return nome_bruto.decode()
    except Exception:
        return nome_bruto.decode(errors="ignore")

for conta in ACCOUNTS:
    email = conta["email"]
    senha = conta["senha"]

    if not email or not senha:
        continue

    mail = conectar_gmail(email, senha)

    if mail:
        print(f"\n📂 Pastas disponíveis na conta: {email}")
        status, pastas = mail.list()
        if status == "OK":
            for pasta in pastas:
                nome = decodificar_nome_pasta(pasta)
                print(f" - {nome}")
        else:
            print("[-] Não foi possível listar as pastas.")
        mail.logout()
    else:
        print(f"[-] Falha ao conectar com {email}")
