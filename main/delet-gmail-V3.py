import os
import time
import socket
from dotenv import load_dotenv
import datetime
from imapclient import IMAPClient 
import imaplib

socket.setdefaulttimeout(300)

# Data de corte: 2.1 anos atrás
DATA_CORTE = (datetime.datetime.now() - datetime.timedelta(days=int(365*2.1))).strftime("%d-%b-%Y")

load_dotenv()

ACCOUNTS = [
    {"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},
    {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
    {"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")},
]

IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

def formatar_tamanho(bytes):
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
        imaplib._MAXLINE = 10_000_000
        mail = IMAPClient(IMAP_SERVER, port=IMAP_PORT, ssl=True)
        mail.login(email, senha)
        return mail
    except Exception as e:
        print(f"[-] Erro ao conectar: {e}")
        return None

def listar_pastas_legiveis(mail):
    try:
        folders = mail.list_folders()
        return [f[2] for f in folders]
    except Exception as e:
        print(f"[-] Erro ao listar pastas: {e}")
        return []

def verificar_conexao(mail):
    try:
        mail.noop()
        return True
    except:
        return False

def limpar_pasta(mail, pasta, email, senha, data_corte):
    try:
        print(f"\n[📁] Processando pasta: {pasta}")
        try:
            mail.select_folder(pasta, readonly=False)
            print(f"[✓] Pasta selecionada: {pasta}")
        except Exception as e:
            print(f"[-] Erro ao selecionar pasta: {str(e)}")
            return False

        data_corte_datetime = datetime.datetime.strptime(data_corte, "%d-%b-%Y")
        print(f"[📅] Data de corte configurada: {data_corte} ({data_corte_datetime.date()})")

        todos_ids = mail.search(['ALL'])
        apagar_ids = []

        for uid in todos_ids:
            try:
                envelope = mail.fetch([uid], ['ENVELOPE'])[uid][b'ENVELOPE']
                data_email = envelope.date.replace(tzinfo=None)
                if data_email.date() <= data_corte_datetime.date():
                    apagar_ids.append(uid)
            except Exception as e:
                print(f"[-] Erro ao obter data do e-mail UID {uid}: {str(e)}")
                continue

        total = len(apagar_ids)

        if total == 0:
            print(f"[!] Nenhum e-mail encontrado em '{pasta}' anterior ou igual a {data_corte}")
            return True

        print(f"[ℹ] Encontrados {total} e-mails para deletar")

        batch_size = 100
        for i in range(0, total, batch_size):
            batch = apagar_ids[i:i+batch_size]
            try:
                mail.add_flags(batch, [b'\\Deleted'])
                mail.expunge()
                percent = min((i + len(batch)) / total * 100, 100)
                bar = '█' * int(percent//2) + '-' * (50-int(percent//2))
                print(f"\r[{bar}] {min(i+len(batch), total)}/{total} ({percent:.1f}%)", end="", flush=True)
            except Exception as e:
                print(f"\n[-] Erro no lote: {str(e)}")
                if not verificar_conexao(mail):
                    print("[!] Reconectando...")
                    mail.logout()
                    mail = conectar_gmail(email, senha)
                    if mail:
                        mail.select_folder(pasta, readonly=False)
                continue

        print(f"\n[✔] Exclusão concluída para '{pasta}'")
        return True

    except Exception as e:
        print(f"\n[-] ERRO em '{pasta}': {str(e)}")
        return False

def limpar_conta_completa(email, senha, data_corte):
    mail = conectar_gmail(email, senha)
    if not mail:
        return

    try:
        print("\n📂 Listando pastas disponíveis:")
        pastas_disponiveis = listar_pastas_legiveis(mail)
        for p in pastas_disponiveis:
            print(f"-> {repr(p)}")

        pastas_prioridade = [
            "INBOX",
            "[Gmail]/All Mail",
            "[Gmail]/Trash",
            "[Gmail]/Sent Mail",
            "[Gmail]/Spam",
            "[Gmail]/Starred",
            "[Gmail]/Drafts",
            "[Gmail]/Important",
            "facul"
        ]

        outras_pastas = [p for p in pastas_disponiveis if p not in pastas_prioridade]
        pastas = pastas_prioridade + outras_pastas

        print(f"\n[🔍] Iniciando limpeza COMPLETA para {email}")

        for pasta in pastas:
            try:
                if not verificar_conexao(mail):
                    print("[!] Reconectando...")
                    mail = conectar_gmail(email, senha)
                    if not mail:
                        return
                limpar_pasta(mail, pasta, email, senha, data_corte)
            except Exception as e:
                print(f"[-] Erro ao processar pasta {pasta}: {str(e)}")
                continue

        print("\n[🔎] Verificação final...")
        for pasta in pastas:
            try:
                mail.select_folder(pasta)
                remaining = mail.search(['ALL'])
                if not remaining:
                    continue

                data_corte_datetime = datetime.datetime.strptime(data_corte, "%d-%b-%Y")
                apagar_ids = []

                for uid in remaining:
                    try:
                        envelope = mail.fetch([uid], ['ENVELOPE'])[uid][b'ENVELOPE']
                        data_email = envelope.date.replace(tzinfo=None)
                        if data_email.date() <= data_corte_datetime.date():
                            apagar_ids.append(uid)
                        else:
                            print(f"[⚠] UID {uid} em '{pasta}' é recente ({data_email.date()}), não será apagado.")
                    except Exception as e:
                        print(f"[-] Erro ao verificar UID {uid} na verificação final: {str(e)}")

                if apagar_ids:
                    print(f"[🔒] Deletando {len(apagar_ids)} e-mails antigos restantes em '{pasta}'...")
                    mail.delete_messages(apagar_ids)
                    mail.expunge()
                else:
                    print(f"[⏭] Nenhum e-mail seguro para apagar em '{pasta}'")

            except Exception as e:
                print(f"[-] Erro na verificação final: {str(e)}")
                continue

        print("\n[🔁] Expurgo reforçado em All Mail e Trash...")
        try:
            mail.select_folder('[Gmail]/All Mail', readonly=False)
            remaining = mail.search(['ALL'])
            if remaining:
                print(f"[🔁] Movendo {len(remaining)} e-mails de '[Gmail]/All Mail' para '[Gmail]/Trash'...")
                mail.move(remaining, '[Gmail]/Trash')
        except Exception as e:
            print(f"[-] Erro durante expurgo reforçado: {str(e)}")

    except Exception as e:
        print(f"[-] Erro ao processar a conta completa: {str(e)}")

# Executa a limpeza em todas as contas
for conta in ACCOUNTS:
    limpar_conta_completa(conta["email"], conta["senha"], DATA_CORTE)
