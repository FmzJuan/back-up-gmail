### ESSE CODIGO ESTA PAGANDO CORRETAMENTE ###

import imaplib
import os
import time
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

ACCOUNTS = [
    {"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},
    {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
    {"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")}
]

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

def conectar_gmail(email, senha):
    """Conecta ao servidor IMAP do Gmail"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(email, senha)
        return mail
    except Exception as e:
        print(f"[-] Erro ao conectar: {e}")
        return None

def listar_pastas(mail):
    """Lista todas as pastas disponíveis"""
    try:
        status, pastas = mail.list()
        if status == "OK":
            return [p.decode().split('"')[-2] for p in pastas if b'"/"' in p]
        return []
    except Exception as e:
        print(f"[-] Erro ao listar pastas: {e}")
        return []

def limpar_pasta(mail, pasta):
    """Apaga todos os e-mails de uma pasta com barra de progresso"""
    try:
        print(f"\n[📁] Processando: {pasta}")
        
        # Seleciona a pasta em modo leitura/escrita
        status, _ = mail.select(pasta, readonly=False)
        if status != "OK":
            print(f"[-] Falha ao acessar pasta '{pasta}'")
            return False

        # Busca todos os e-mails
        status, data = mail.search(None, "ALL")
        if status != "OK":
            print(f"[-] Erro ao buscar e-mails em '{pasta}'")
            return False

        # Converte os IDs de bytes para string
        email_ids = data[0].split()
        total = len(email_ids)
        
        if total == 0:
            print(f"[!] Nenhum e-mail em '{pasta}'")
            return True

        print(f"[🗑️] Apagando {total} e-mails...")
        print("[", end="", flush=True)

        # Processa em lotes de 50 e-mails
        for i in range(0, total, 50):
            batch = email_ids[i:i+50]
            
            # Converte os bytes para strings
            str_batch = [id.decode('utf-8') for id in batch]
            mail.store(','.join(str_batch), '+FLAGS', '\\Deleted')
            
            # Atualiza a barra de progresso
            progresso = min(i + 50, total)
            percentual = int((progresso / total) * 100)
            num_igual = int(percentual / 5)
            print("=" * max(1, num_igual - int(i/250)), end="", flush=True)
            time.sleep(0.05)

        print("] 100%")
        
        # Expurga os e-mails marcados como deletados
        mail.expunge()
        print(f"[✔] {total} e-mails apagados de '{pasta}'")
        return True

    except Exception as e:
        print(f"\n[-] ERRO em '{pasta}': {str(e)}")
        return False

def limpar_conta(email, senha):
    """Limpa todas as pastas da conta"""
    mail = conectar_gmail(email, senha)
    if not mail:
        return

    try:
        pastas = listar_pastas(mail)
        if not pastas:
            print("[-] Nenhuma pasta encontrada")
            return

        print(f"\n[🔍] Iniciando limpeza para {email}")
        print("[⚠️] ATENÇÃO: TODOS os e-mails serão APagados!")
        
        # Pastas padrão do Gmail em português
        pastas_prioritarias = [
            'INBOX',
            '[Gmail]/Lixeira',
            '[Gmail]/Spam',
            '[Gmail]/Todos os e-mails',
            '[Gmail]/Enviados',
            '[Gmail]/Rascunhos'
        ]

        # Primeiro limpa as pastas prioritárias
        for pasta in pastas_prioritarias:
            if pasta in pastas:
                limpar_pasta(mail, pasta)

        # Depois limpa outras pastas personalizadas
        for pasta in pastas:
            if pasta not in pastas_prioritarias:
                limpar_pasta(mail, pasta)

    finally:
        mail.close()
        mail.logout()
        print(f"\n[🎉] Processo concluído para {email}!")
        print("[❗] Verifique sua conta para confirmar a limpeza.")

if __name__ == "__main__":
    print("=============================================")
    print(" LIMPEZA TOTAL DE CAIXA DE E-MAIL ")
    print("=============================================")
    print("[❗] AVISO: Esta ação é IRREVERSÍVEL!")
    print("=============================================\n")
    
    confirmacao = input("Digite 'SIM' para confirmar: ")
    
    if confirmacao.upper() == 'SIM':
        for acc in ACCOUNTS:
            if acc["email"] and acc["senha"]:
                limpar_conta(acc["email"], acc["senha"])
    else:
        print("\n[🚫] Operação cancelada pelo usuário")