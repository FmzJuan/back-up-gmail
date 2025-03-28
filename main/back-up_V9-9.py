import imaplib
import os
import time
import sys
import locale
import signal
import quopri
import mimetypes
from email import message_from_bytes
from email.header import decode_header
from email.policy import default as default_policy
from email import policy
from email.parser import BytesParser
from dotenv import load_dotenv
import humanize
from datetime import datetime, timedelta
import config
import re
import base64
import chardet
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
# Configurações globais
load_dotenv()
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
BACKUP_DIR = "backup_emails"
MAX_RETRIES = 3
TIMEOUT = 300

class BackupManager:
    def __init__(self):
        self.accounts = [
            {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
            {"email": os.getenv("EMAIL_4"), "senha": os.getenv("SENHA_4")},
        ]
        self.interrupted = False
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        print("\n\n[!] Interrompendo backup... Aguarde")
        self.interrupted = True

    def configure_encoding(self):
        """Configura o ambiente para suporte a múltiplos encodings"""
        locale_variants = ['en_US.UTF-8', 'C.UTF-8', 'pt_BR.UTF-8', '']
        for loc in locale_variants:
            try:
                locale.setlocale(locale.LC_ALL, loc)
                break
            except locale.Error:
                continue
        # Força UTF-8 para toda a saída
        sys.stdout.reconfigure(encoding='utf-8', errors='replace') if hasattr(sys.stdout, 'reconfigure') else None

    def decode_email_content(self, payload, charset=None):
        """
        Decodifica o conteúdo do email com suporte robusto a Unicode
        """
        if isinstance(payload, bytes):
            # Primeiro tenta detectar o encoding automaticamente
            detected = chardet.detect(payload)
            detected_encoding = detected['encoding'] if detected['confidence'] > 0.7 else None
            
            # Lista de encodings para tentar (em ordem de prioridade)
            encodings = [
                charset,
                detected_encoding,
                'utf-8',
                'latin-1',
                'iso-8859-1',
                'shift_jis',  # Japonês
                'euc-jp',     # Japonês
                'gb2312',     # Chinês Simplificado
                'gbk',        # Chinês Simplificado
                'big5',       # Chinês Tradicional
                'euc-kr',     # Coreano
                'utf-16',
                'utf-16le',
                'utf-16be'
            ]
            
            # Remove None e duplicados
            encodings = [e for e in encodings if e is not None]
            seen = set()
            encodings = [e for e in encodings if not (e in seen or seen.add(e))]
            
            # Tenta decodificar com cada encoding
            for encoding in encodings:
                try:
                    return payload.decode(encoding)
                except UnicodeDecodeError:
                    continue
            
            # Fallback final - substitui caracteres inválidos
            return payload.decode('utf-8', errors='replace')
        return payload

    def fix_quoted_printable(self, text):
        """
        Corrige manualmente caracteres Quoted-Printable mal formatados
        """
        if not isinstance(text, str):
            return text
            
        # Remove quebras de linha do QP
        text = re.sub(r'=\r?\n', '', text)
        
        # Substitui códigos QP por caracteres
        def replace_qp(match):
            hex_str = match.group(1)
            try:
                return chr(int(hex_str, 16))
            except:
                return match.group(0)
                
        text = re.sub(r'=([0-9A-Fa-f]{2})', replace_qp, text)
        return text

    def process_email_payload(self, msg):
        """
        Processa o payload do email, preservando toda a estrutura original
        """
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                charset = part.get_content_charset()
                
                # Para partes binárias (imagens, anexos), não decodificar
                if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition', '').startswith('attachment'):
                    continue
                
                # Para conteúdo textual, decodificar corretamente
                if content_type in ['text/plain', 'text/html']:
                    payload = part.get_payload(decode=True)
                    if payload is not None:
                        decoded = self.decode_email_content(payload, charset)
                        # Mantém a codificação original se for Quoted-Printable ou Base64
                        transfer_encoding = part.get('Content-Transfer-Encoding', '').lower()
                        if transfer_encoding == 'quoted-printable':
                            decoded = self.fix_quoted_printable(decoded)
                            part.set_payload(decoded)
                            part.set_charset('utf-8')
                        elif transfer_encoding == 'base64':
                            # Mantém como base64 para preservação exata
                            part.set_payload(payload)
                        else:
                            part.set_payload(decoded)
                            part.set_charset('utf-8')
        else:
            # Email não multipart
            payload = msg.get_payload(decode=True)
            if payload is not None:
                charset = msg.get_content_charset()
                decoded = self.decode_email_content(payload, charset)
                transfer_encoding = msg.get('Content-Transfer-Encoding', '').lower()
                if transfer_encoding == 'quoted-printable':
                    decoded = self.fix_quoted_printable(decoded)
                    msg.set_payload(decoded)
                    msg.set_charset('utf-8')
                elif transfer_encoding == 'base64':
                    msg.set_payload(payload)
                else:
                    msg.set_payload(decoded)
                    msg.set_charset('utf-8')

    def mostrar_barra_progresso(self, atual, total, tamanho=50, velocidade="", tempo_restante=""):
        """Mostra uma barra de progresso no terminal"""
        percentual = atual / total if total > 0 else 0
        barras = '█' * int(tamanho * percentual)
        espacos = ' ' * (tamanho - len(barras))
        
        status = f"{atual}/{total} ({percentual:.1%})"
        if velocidade and tempo_restante:
            status += f" | {velocidade}/s | {tempo_restante} restante"
        
        sys.stdout.write(f"\r[{barras}{espacos}] {status}")
        sys.stdout.flush()

    def select_folder_safely(self, mail, folder_name):
        """Seleciona uma pasta de e-mail com tratamento seguro"""
        try:
            if folder_name.startswith('[Gmail]'):
                if folder_name == '[Gmail]':
                    return "SKIP", None
                
                for attempt in [f'"{folder_name}"', folder_name]:
                    try:
                        status, data = mail.select(attempt, readonly=True)
                        if status == "OK":
                            return status, data
                    except Exception:
                        continue
                return "ERROR", None
            
            if ' ' in folder_name:
                return mail.select(f'"{folder_name}"', readonly=True)
            return mail.select(folder_name, readonly=True)
        except Exception as e:
            print(f"[-] Erro ao selecionar pasta {folder_name}: {str(e)}")
            return "ERROR", None

    def conectar_gmail(self, email, senha):
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=30)
            mail.socket().settimeout(TIMEOUT)
            mail.login(email, senha)
            return mail
        except Exception as e:
            print(f"[-] Erro ao conectar {email}: {str(e)}")
            return None

    def reconectar(self, mail, email, senha):
        print("[!] Tentando reconectar...")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                mail.shutdown()
                time.sleep(5 * attempt)
                new_mail = self.conectar_gmail(email, senha)
                if new_mail:
                    print(f"[✔] Reconectado na tentativa {attempt}")
                    return new_mail
            except Exception as e:
                print(f"[-] Falha na tentativa {attempt}: {str(e)}")
        return None

    def listar_pastas(self, mail):
        try:
            status, pastas = mail.list()
            if status == "OK":
                pastas_validas = []
                for p in pastas:
                    try:
                        pasta = p.decode().split(' "/" ')[-1].strip('"')
                        if '[Gmail]' in pasta and pasta != '[Gmail]':
                            if pasta not in pastas_validas:
                                pastas_validas.append(pasta)
                        elif pasta != '[Gmail]' and pasta not in pastas_validas:
                            pastas_validas.append(pasta)
                    except Exception as e:
                        print(f"[-] Erro ao processar a pasta: {str(e)}")
                        continue
                return pastas_validas
            return []
        except Exception as e:
            print(f"[-] Erro ao listar pastas: {str(e)}")
            return []

    def criar_pastas_backup(self, email, pastas):
        base_dir = os.path.join(BACKUP_DIR, email.split('@')[0])
        try:
            os.makedirs(base_dir, exist_ok=True)
            for pasta in pastas:
                try:
                    # Preserva o máximo possível do nome original
                    safe_name = "".join(c if ord(c) < 128 and c not in '\\/*?:"<>|' else "_" for c in pasta)
                    pasta_path = os.path.join(base_dir, safe_name.replace('/', os.path.sep))
                    os.makedirs(pasta_path, exist_ok=True)
                except Exception as e:
                    print(f"[-] Erro ao criar pasta {pasta}: {str(e)}")
            return base_dir
        except Exception as e:
            print(f"[-] Erro ao criar diretório base: {str(e)}")
            return None

    def sanitize_filename(self, filename):
        """Remove caracteres inválidos de nomes de arquivos mantendo Unicode"""
        if not filename:
            return "anexo_sem_nome"
        
        # Substitui apenas caracteres realmente problemáticos
        filename = re.sub(r'[\\/*?:"<>|]', "_", filename)
        
        # Remove caracteres de controle
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
        
        # Limita o tamanho do nome do arquivo
        return filename[:200] if len(filename) > 200 else filename

    def decode_header_complete(self, header):
        """Decodifica completamente um cabeçalho de email com suporte a Unicode"""
        if header is None:
            return ""
            
        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                try:
                    decoded = part.decode(encoding or 'utf-8', errors='replace')
                except UnicodeDecodeError:
                    try:
                        decoded = part.decode('latin-1', errors='replace')
                    except:
                        decoded = part.decode('utf-8', errors='replace')
                decoded_parts.append(decoded)
            else:
                decoded_parts.append(str(part))
        return ' '.join(decoded_parts)

    def salvar_email(self, uid, msg, caminho):
        try:
            # Preserva a política original
            msg.policy = policy.default
            
            # Decodifica o assunto corretamente
            assunto = self.decode_header_complete(msg.get("Subject", "Sem Assunto"))
            
            # Processa o conteúdo mantendo a estrutura original
            self.process_email_payload(msg)
            
            # Cria nome de arquivo seguro mantendo Unicode
            safe_subject = self.sanitize_filename(assunto)[:100] or "email"
            safe_uid = self.sanitize_filename(uid)
            
            # Garante que o caminho existe
            os.makedirs(caminho, exist_ok=True)
            
            # Cria o nome do arquivo principal
            email_filename = os.path.join(caminho, f"{safe_uid}_{safe_subject}.eml")
            
            # Tenta salvar com Unicode
            try:
                with open(email_filename, "wb") as f:
                    f.write(msg.as_bytes(policy=policy.default))
            except (UnicodeEncodeError, OSError) as e:
                # Fallback para nome ASCII se Unicode falhar
                email_filename = os.path.join(caminho, f"{safe_uid}_email.eml")
                with open(email_filename, "wb") as f:
                    f.write(msg.as_bytes(policy=policy.default))

            total_size = os.path.getsize(email_filename)
            anexos_salvos = []

            if msg.is_multipart():
                anexos_dir = os.path.join(caminho, f"{safe_uid}_anexos")
                try:
                    os.makedirs(anexos_dir, exist_ok=True)
                except (UnicodeEncodeError, OSError):
                    anexos_dir = os.path.join(caminho, f"{safe_uid}_anexos")
                    os.makedirs(anexos_dir, exist_ok=True)

                for part in msg.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue

                    filename = part.get_filename()
                    content_disposition = str(part.get("Content-Disposition", "")).lower()

                    if filename or 'attachment' in content_disposition or part.get_content_type().startswith('image/'):
                        try:
                            # Decodificação do nome do arquivo
                            if filename:
                                filename = self.decode_header_complete(filename)
                                filename = self.sanitize_filename(filename)
                            
                            if not filename:
                                # Cria um nome baseado no tipo de conteúdo
                                ext = mimetypes.guess_extension(part.get_content_type()) or '.bin'
                                filename = f"anexo_{int(time.time())}{ext}"

                            # Define extensão apropriada
                            ext = mimetypes.guess_extension(part.get_content_type()) or '.bin'
                            if not filename.lower().endswith(ext.lower()):
                                name, old_ext = os.path.splitext(filename)
                                filename = f"{name}{ext}"

                            filepath = os.path.join(anexos_dir, filename)

                            # Evita sobrescrita
                            counter = 1
                            while os.path.exists(filepath):
                                name, ext = os.path.splitext(filename)
                                filepath = os.path.join(anexos_dir, f"{name}_{counter}{ext}")
                                counter += 1

                            # Salva o anexo exatamente como recebido
                            payload = part.get_payload(decode=True)
                            if payload:  # Só salva se houver conteúdo
                                with open(filepath, "wb") as f:
                                    f.write(payload)
                                
                                anexos_salvos.append(filepath)
                                total_size += os.path.getsize(filepath)

                        except Exception as e:
                            print(f"[-] Erro ao processar anexo: {str(e)}")
                            continue

            return True, total_size, anexos_salvos

        except Exception as e:
            print(f"[-] Erro crítico ao salvar e-mail {uid}: {str(e)}")
            return False, 0, []

    def processar_pasta(self, mail, pasta, account_dir, email, senha):
        print(f"\n[📁] Processando pasta: {pasta}")
        
        total_salvos = total_tamanho = total_anexos = 0
        retries = 0
        
        def reconectar_e_reselecionar():
            nonlocal mail, retries
            mail = self.reconectar(mail, email, senha)
            if not mail:
                return False
            retries += 1
            status, _ = self.select_folder_safely(mail, pasta)
            return status == "OK"
        
        while retries < MAX_RETRIES and not self.interrupted:
            try:
                status, _ = self.select_folder_safely(mail, pasta)
                
                if status == "SKIP":
                    print(f"[ℹ] Pasta {pasta} é um container, pulando...")
                    return 0, 0, 0
                elif status != "OK":
                    print(f"[-] Falha ao selecionar pasta {pasta} (tentativa {retries+1}/{MAX_RETRIES})")
                    if not reconectar_e_reselecionar():
                        continue
                    else:
                        return 0, 0, 0

                status, messages = mail.uid("SEARCH", None, f'(ON "{config.DATA_CORTE}")')
                
                if status != "OK" or not messages[0]:
                    print(f"[ℹ] Nenhum e-mail encontrado em {pasta} para a data especificada")
                    return 0, 0, 0
                
                email_uids = messages[0].split()
                safe_folder_name = self.sanitize_filename(pasta)
                caminho_pasta = os.path.join(account_dir, safe_folder_name.replace('/', os.path.sep))
                os.makedirs(caminho_pasta, exist_ok=True)
                
                start_time = time.time()
                total_emails = len(email_uids)

                for i, uid in enumerate(email_uids, 1):
                    if self.interrupted:
                        break
                        
                    try:
                        if i % 10 == 0:
                            mail.noop()
                        
                        status, data = mail.uid("FETCH", uid, "(BODY.PEEK[] RFC822.SIZE)")
                        if status == "OK" and data and isinstance(data[0], tuple):
                            raw_email = data[0][1]
                            msg = message_from_bytes(raw_email, policy=policy.default)
                            
                            sucesso, tamanho, anexos = self.salvar_email(uid.decode(), msg, caminho_pasta)
                            if sucesso:
                                total_salvos += 1
                                total_tamanho += tamanho
                                total_anexos += len(anexos)
                                
                                elapsed = time.time() - start_time
                                speed = humanize.naturalsize(total_tamanho / elapsed) if elapsed > 0 else "0 B"
                                avg_time = elapsed / i if i > 0 else 0
                                remaining = humanize.precisedelta(timedelta(seconds=max(0, (total_emails - i) * avg_time)))
                                
                                status_msg = f"{i}/{total_emails} | Anexos: {total_anexos} | {speed}/s"
                                self.mostrar_barra_progresso(i, total_emails, velocidade=status_msg, tempo_restante=remaining)
                    
                    except (imaplib.IMAP4.abort, ConnectionError) as e:
                        print(f"\n[!] Erro de conexão: {str(e)}")
                        if not reconectar_e_reselecionar():
                            raise
                        continue
                        
                    except Exception as e:
                        print(f"\n[-] Erro ao processar e-mail: {str(e)}")
                        continue
                
                if not self.interrupted:
                    print(f"\n[✔] Concluído: {total_salvos} e-mails, {total_anexos} anexos ({humanize.naturalsize(total_tamanho)})")
                return total_salvos, total_tamanho, total_anexos
            
            except (imaplib.IMAP4.abort, ConnectionError) as e:
                print(f"\n[!] Erro de conexão na pasta {pasta}: {str(e)}")
                if not reconectar_e_reselecionar():
                    break
                continue
                
            except Exception as e:
                print(f"\n[-] Erro inesperado ao processar pasta {pasta}: {str(e)}")
                break
        
        return total_salvos, total_tamanho, total_anexos

    def realizar_backup(self):
        """Função principal para realizar o backup"""
        print("\n[❗] Pressione Ctrl+C para interromper o backup")
        
        try:
            for account in self.accounts:
                if self.interrupted:
                    break
                    
                email, senha = account["email"], account["senha"]
                if not email or not senha:
                    print(f"[-] Credenciais não encontradas para uma conta")
                    continue
                    
                print(f"\n[🔍] Iniciando backup para: {email}")
                
                mail = self.conectar_gmail(email, senha)
                if not mail:
                    continue
                
                try:
                    pastas = self.listar_pastas(mail)
                    if not pastas:
                        print(f"[⚠] Nenhuma pasta encontrada para {email}")
                        continue
                    
                    print(f"[ℹ] Pastas encontradas: {', '.join(pastas)}")
                    account_dir = self.criar_pastas_backup(email, pastas)
                    if not account_dir:
                        continue
                        
                    total_emails_conta = 0
                    total_tamanho_conta = 0
                    total_anexos_conta = 0
                    
                    for pasta in pastas:
                        if self.interrupted:
                            break
                            
                        salvos, tamanho, anexos = self.processar_pasta(mail, pasta, account_dir, email, senha)
                        total_emails_conta += salvos
                        total_tamanho_conta += tamanho
                        total_anexos_conta += anexos
                    
                    if not self.interrupted:
                        print(f"\n[🎉] Backup concluído para {email}")
                        print(f"  ↳ Total de e-mails: {total_emails_conta}")
                        print(f"  ↳ Total de anexos: {total_anexos_conta}")
                        print(f"  ↳ Tamanho total: {humanize.naturalsize(total_tamanho_conta)}")
                
                finally:
                    try:
                        mail.logout()
                    except Exception:
                        pass
            
            if not self.interrupted:
                print("\n[✔✔✔] Todos os backups concluídos com sucesso!")
                
        except KeyboardInterrupt:
            self.interrupted = True
            print("\n[!] Backup interrompido pelo usuário")
        except Exception as e:
            print(f"\n[‼] Erro fatal durante o backup: {str(e)}")

if __name__ == "__main__":
    # Configuração inicial do sistema
    if sys.version_info[0] == 3:
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            pass
    
    backup_manager = BackupManager()
    backup_manager.configure_encoding()
    backup_manager.realizar_backup()