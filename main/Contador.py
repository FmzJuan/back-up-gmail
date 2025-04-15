import imaplib
import email
from datetime import datetime, timedelta
from tqdm import tqdm
from dotenv import load_dotenv
import os
import re

# Carrega variáveis do .env
load_dotenv()

# Configurações
IMAP_SERVIDOR = "imap.gmail.com"
DIAS_CORTE = 3 * 365  # 3 anos

# Lista de contas
ACCOUNTS = [
    {"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},
    {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
    {"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")},
    #{"email": os.getenv("EMAIL_4"), "senha": os.getenv("SENHA_4")},
    {"email": os.getenv("EMAIL_5"), "senha": os.getenv("SENHA_5")},
    {"email": os.getenv("EMAIL_6"), "senha": os.getenv("SENHA_6")},
    {"email": os.getenv("EMAIL_7"), "senha": os.getenv("SENHA_7")},
]

def conectar_imap(email, senha):
    mail = imaplib.IMAP4_SSL(IMAP_SERVIDOR)
    mail.login(email, senha)
    return mail

def obter_pastas(mail):
    status, pastas = mail.list()
    if status != 'OK' or not pastas:
        return []
    return [linha.split(b' "/" ')[1].strip(b'"').decode() for linha in pastas]

def buscar_emails(mail, pasta, data_corte):
    try:
        # Select the folder with proper encoding and handle special folders
        if pasta == '[Gmail]':
            return []  # Skip the root [Gmail] folder as it can't be selected
            
        try:
            status = mail.select(f'"{pasta}"' if ' ' in pasta or '[' in pasta else pasta, readonly=True)
        except:
            return []

        data_formatada = data_corte.strftime("%d-%b-%Y")
        status, ids = mail.search(None, f'SINCE {data_formatada}')
        if status != 'OK':
            return []
        return ids[0].split()
    except Exception as e:
        print(f"Erro ao buscar na pasta {pasta}: {e}")
        return []

def calcular_tamanhos(mail, ids):
    total_tamanho = 0
    for msg_id in tqdm(ids, desc="Calculando tamanho", leave=False):
        try:
            # Fetch the entire message to get accurate size
            status, data = mail.fetch(msg_id, '(RFC822)')
            if status == 'OK' and data and data[0] and data[0][1]:
                total_tamanho += len(data[0][1])
        except Exception as e:
            continue
    return total_tamanho

def analisar_conta(email, senha):
    print(f"\n📧 Analisando conta: {email}")
    data_corte = datetime.now() - timedelta(days=DIAS_CORTE)
    try:
        mail = conectar_imap(email, senha)
        pastas = obter_pastas(mail)

        print(f"Data de corte: {data_corte.date()}")
        for pasta in pastas:
            if pasta == '[Gmail]':  # Skip root Gmail folder
                continue
                
            ids = buscar_emails(mail, pasta, data_corte)
            if not ids:
                continue

            tamanho_total = calcular_tamanhos(mail, ids)
            tamanho_mb = tamanho_total / (1024 * 1024)
            if tamanho_mb > 0:  # Only show folders with content
                print(f"📂 Pasta: {pasta}")
                print(f" → Emails: {len(ids)}")
                print(f" → Tamanho total: {tamanho_mb:.2f} MB\n")

        mail.logout()

    except imaplib.IMAP4.error as e:
        print(f"❌ Erro de autenticação na conta {email}: {e}")
    except Exception as e:
        print(f"❌ Erro na conta {email}: {e}")

def main():
    for conta in ACCOUNTS:
        if conta["email"] and conta["senha"]:
            analisar_conta(conta["email"], conta["senha"])

if __name__ == "__main__":
    main()
