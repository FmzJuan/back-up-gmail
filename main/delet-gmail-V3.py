import imaplib
import os
import time
import socket
from dotenv import load_dotenv
from config import DATA_CORTE

# Configurar timeout global
socket.setdefaulttimeout(60)

# Carregar variáveis de ambiente
load_dotenv()

ACCOUNTS = [
    #{"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},# juanmeneghesso2
    #{"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},# juan.investur
    #{"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")},# jmenega3
    {"email": os.getenv("EMAIL_4"),  "senha": os.getenv("SENHA_4")},# anderson.investur 
    #{"email": os.getenv("EMAIL_5"),# "senha": os.getenv("SENHA_5")}# silvia.investur
    
]

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

def formatar_tamanho(bytes):
    """Formata o tamanho em bytes para kB/MB/GB"""
    if bytes < 1024:
        return f"{bytes} bytes"
    elif bytes < 1024*1024:
        return f"{bytes/1024:.1f} kB"
    elif bytes < 1024*1024*1024:
        return f"{bytes/(1024*1024):.1f} MB"
    else:
        return f"{bytes/(1024*1024*1024):.1f} GB"

def conectar_gmail(email, senha):
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email, senha)
        return mail
    except Exception as e:
        print(f"[-] Erro ao conectar: {e}")
        return None

def listar_pastas(mail):
    try:
        status, pastas = mail.list()
        if status == "OK":
            return [p.decode().split('"')[-2] for p in pastas if b'"/"' in p]
        return []
    except Exception as e:
        print(f"[-] Erro ao listar pastas: {e}")
        return []

def limpar_pasta(mail, pasta):
    try:
        print(f"\n[📁] Processando pasta: {pasta}")

        # Configurar timeout mais longo
        mail.socket().settimeout(120)

        # Tratamento especial para pastas do Gmail
        if pasta.startswith('[Gmail]'):
            status, _ = mail.select(f'"{pasta}"', readonly=False)
        else:
            status, _ = mail.select(pasta, readonly=False)

        if status != "OK":
            print(f"[-] Falha ao acessar pasta '{pasta}'")
            return False

        # Buscar TODOS os e-mails
        status, data = mail.search(None, "ALL")
        if status != "OK":
            print(f"[-] Erro ao buscar e-mails em '{pasta}'")
            return False

        email_ids = data[0].split()
        total = len(email_ids)

        if total == 0:
            print("[!] Nenhum e-mail encontrado")
            return True

        # Variáveis para cálculo de progresso
        start_time = time.time()
        processed_size = 0
        avg_speed = 108.0

        for i, email_id in enumerate(email_ids, 1):
            try:
                # Tentar várias vezes para e-mails com anexos
                for tentativa in range(3):
                    try:
                        mail.store(email_id, '+FLAGS', '\\Deleted')
                        break
                    except Exception as e:
                        if tentativa == 2:
                            raise
                        time.sleep(2)
                
                # Simulação de tamanho
                processed_size += 3 * 1024
                elapsed_time = time.time() - start_time
                speed = processed_size / elapsed_time if elapsed_time > 0 else 0
                avg_speed = (avg_speed + speed) / 2
                
                # Calcular progresso
                percent = (i / total) * 100
                remaining = (total - i) * (elapsed_time / i) if i > 0 else 0
                
                # Barra de progresso
                bar_length = 50
                filled_length = int(bar_length * i // total)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                
                print(f"\r[{bar}] {i}/{total} ({percent:.1f}%) | {formatar_tamanho(avg_speed)}/s | {int(remaining)} seconds remaining", end="", flush=True)
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"\n[-] Erro ao apagar e-mail {email_id}: {str(e)}")
                continue

        # Confirmar exclusão
        mail.expunge()
        print(f"\n[✔] {total} e-mails apagados de '{pasta}'")
        return True

    except Exception as e:
        print(f"\n[-] ERRO em '{pasta}': {str(e)}")
        return False

def limpar_conta_completa(email, senha):
    mail = conectar_gmail(email, senha)
    if not mail:
        return

    try:
        pastas = listar_pastas(mail)
        if not pastas:
            print("[-] Nenhuma pasta encontrada")
            return

        print(f"\n[🔍] Iniciando limpeza TOTAL para {email}")
        print("[⚠️] ATENÇÃO: TODOS os e-mails serão apagados permanentemente!")

        # Pastas prioritárias atualizadas
        pastas_prioritarias = [
            'INBOX',
            '"INBOX"',
            '[Gmail]/Todos os e-mails',
            '"[Gmail]/Todos os e-mails"',
            '[Gmail]/Lixeira',
            '"[Gmail]/Lixeira"',
            '[Gmail]/Spam',
            '"[Gmail]/Spam"',
            '[Gmail]/Enviados',
            '"[Gmail]/Enviados"',
            '[Gmail]/Rascunhos',
            '"[Gmail]/Rascunhos"',
            'INBOX/primary',
            '"INBOX/primary"',
            'INBOX/promotions',
            '"INBOX/promotions"',
            'INBOX/social',
            '"INBOX/social"',
            '[Gmail]/CatPromo',
            '[Gmail]/CatSocial',
            '[Gmail]/CatPrincipal'
        ]

        # Primeiro limpa as pastas prioritárias
        for pasta in pastas_prioritarias:
            if pasta.strip('"') in pastas:
                limpar_pasta(mail, pasta)

        # Depois limpa todas as outras pastas
        for pasta in pastas:
            if pasta not in [p.strip('"') for p in pastas_prioritarias]:
                limpar_pasta(mail, pasta)

    finally:
        mail.close()
        mail.logout()
        print(f"\n[🎉] LIMPEZA TOTAL CONCLUÍDA PARA {email}!")
        print("[❗] Verifique sua conta para confirmar.")

if __name__ == "__main__":
    print("=============================================")
    print(" LIMPEZA COMPLETA DE CAIXA DE E-MAIL ")
    print("=============================================")
    print("[❗] AVISO: Esta ação é IRREVERSÍVEL!")
    print("=============================================\n")

    confirmacao = input("Digite 'APAGAR TUDO' para confirmar: ")

    if confirmacao.upper() == 'APAGAR TUDO':
        for acc in ACCOUNTS:
            if acc["email"] and acc["senha"]:
                limpar_conta_completa(acc["email"], acc["senha"])
    else:
        print("\n[🚫] Operação cancelada")