import os
import time
import socket
from dotenv import load_dotenv
import datetime
from imapclient import IMAPClient 
import imaplib
import sys
import argparse

socket.setdefaulttimeout(300)

# Argumento para modo dry-run
parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', action='store_true', help='Simular a limpeza sem apagar nada')
args = parser.parse_args()
DRY_RUN = args.dry_run

# DATA_CORTE: apagar todos os e-mails com data ANTERIOR a este valor
# Adicionando +1 dia para garantir que "hoje" também seja incluído
#("aqui ele realmete muda")
# Em vez de para portugues :
#DATA_CORTE = (datetime.datetime.now() - datetime.timedelta(days=0)).strftime("%d-%b-%Y")
# use para ingles :
#DATA_CORTE = (datetime.datetime.now() - datetime.timedelta(days=0)).strftime("%Y/%m/%d")
#configuração nova para tratamento de all emails em seach de data do gmail abaixo
hoje = datetime.datetime.now()
DATA_CORTE_IMAP   = (hoje - datetime.timedelta(days=-1)).strftime("%d-%b-%Y")   # e.g. "27-Jun-2025"
DATA_CORTE_GMAIL  = (hoje - datetime.timedelta(days=-1)).strftime("%Y/%m/%d")   # e.g. "2025/06/27"




load_dotenv()

ACCOUNTS = [
 
    {"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")},
    {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")}
    
]

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993


def conectar_gmail(email, senha):
    try:
        imaplib._MAXLINE = 10_000_000
        mail = IMAPClient(IMAP_SERVER, port=IMAP_PORT, ssl=True)
        mail.login(email, senha)
        return mail
    except Exception as e:
        print(f"[!] Falha ao conectar na conta {email}: {e}")
        return None


def listar_pastas_legiveis(mail):
    try:
        folders = mail.list_folders()
        return [f[2] for f in folders]
    except:
        return []


def verificar_conexao(mail):
    try:
        mail.noop()
        return True
    except:
        return False


def limpar_pasta(mail, pasta, email, senha):
    try:
        mail.select_folder(pasta, readonly=False)

        # Busca mensagens por data ou todas, conforme a pasta
        if pasta == '[Gmail]/All Mail':
            #Gmail search respeitando data
            #mensagens_antigas = mail.gmail_search(f'before:{DATA_CORTE}')
            #mensagens_antigas = mail.gmail_search('in:anywhere')
            #mensagens_antigas = mail.gmail_search('in:anywhere')
            #mensagens_antigas = mail.gmail_search(f'in:anywhere before:{DATA_CORTE}')
            mensagens_antigas = mail.gmail_search(f'in:anywhere before:{DATA_CORTE_GMAIL}')
        else:
            #mensagens_antigas = mail.search(['BEFORE', DATA_CORTE])
            mensagens_antigas = mail.search(['BEFORE', DATA_CORTE_IMAP])


        total = len(mensagens_antigas)
        print(f"[DEBUG] Labels dos primeiros 5 e-mails:")
        for uid in mensagens_antigas:
            try:
                labels = mail.fetch([uid], ['X-GM-LABELS'])
                print(f"UID {uid}: {labels[uid][b'X-GM-LABELS']}")
            except Exception as e:
                print(f"Erro ao buscar labels do UID {uid}: {e}")

        if total == 0:
            print(f"[{email}] Nenhum e-mail antigo encontrado em '{pasta}' antes de {DATA_CORTE_IMAP}")
            return True

        print(f"[{email}] Limpando pasta: {pasta} ({total} e-mails encontrados)")
        batch_size = 500
        for i in range(0, total, batch_size):
            batch = mensagens_antigas[i:i+batch_size]

            if DRY_RUN:
                print(f"[SIMULADO] {len(batch)} e-mails seriam apagados de '{pasta}'")
            else:
                try:
                    mail.remove_flags(batch, ['\\Seen', '\\Flagged', '\\Draft', '\\Answered'])  # <-- apenas válidas
                    mail.add_flags(batch, ['\\Deleted'])
                    mail.expunge()
                    print(f"[APAGADO] {len(batch)} e-mails removidos de '{pasta}'")

                except Exception as e:
                    print(f"[ERRO ao apagar batch de '{pasta}']: {e}")
                    continue

        return True

    except Exception as e:
        print(f"[-] ERRO em '{pasta}': {str(e)}")
        return False



def limpar_conta_completa(email, senha):
    mail = conectar_gmail(email, senha)
    if not mail:
        return

    try:
        pastas = listar_pastas_legiveis(mail)
        print(f"Pastas disponíveis em {email}:")
        for p in pastas:
            print("-", p)

        for pasta in pastas:
            if not verificar_conexao(mail):
                mail = conectar_gmail(email, senha)
                if not mail:
                    return
            limpar_pasta(mail, pasta, email, senha)

    except Exception as e:
        print(f"[ERRO GERAL NA CONTA {email}] {e}")

    finally:
        mail.logout()

# Execução principal
for conta in ACCOUNTS:
    print(f"\n=== Processando conta: {conta['email']} ===")
    limpar_conta_completa(conta["email"], conta["senha"])
