## estou ultilizando esse versao anterior e a v8
### aqui no tem problemas 
        ## //apagar esse comentaio depois , ultima pasta que foi puxada : 2022-06-22_19-05-03  //##
#status : ok  -> silvia ,andersonSSS
import imaplib
import os
import datetime
import concurrent.futures

import re
import chardet
import socket
import ssl
import time
from email import message_from_bytes
from email.header import decode_header
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

# Remove the duplicate DATA_CORTE definitions and add this near the top constants
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993
FETCH_TIMEOUT = 300
RETRY_DELAY = 10
MAX_RETRIES = 7
BATCH_SIZE = 5
MAX_THREADS = 2
BACKUP_DIR = "backup_emails"

# Clear definition of date cutoff (2.1 years)

DATA_CORTE = (datetime.datetime.now() - datetime.timedelta(days=int(365 * 2.1))).strftime("%d-%b-%Y")

# Define accounts directly
ACCOUNTS = [
   # {"email": os.getenv("EMAIL_1"), "senha": os.getenv("SENHA_1")},
   # {"email": os.getenv("EMAIL_2"), "senha": os.getenv("SENHA_2")},
   # {"email": os.getenv("EMAIL_3"), "senha": os.getenv("SENHA_3")},
    {"email": os.getenv("EMAIL_5"), "senha": os.getenv("SENHA_5")},
   # {"email": os.getenv("EMAIL_6"), "senha": os.getenv("SENHA_6")}
]

# Simple account filtering
ACCOUNTS = [acc for acc in ACCOUNTS if acc["email"] and acc["senha"]]

# Move PASTAS list right after the constants, before ACCOUNTS definition
PASTAS = [
    #juanmeneghesso2@gmail.com
    #"INBOX",
    #"[Gmail]/All Mail",
    #"[Gmail]/Trash",
    #"[Gmail]/Sent Mail",
    #"[Gmail]/Spam",
    #"[Gmail]/Starred",
    #"[Gmail]/Drafts",
    
    #juan.investur@gmail.com
    #"INBOX",
    "[Gmail]/All Mail",
    "[Gmail]/Drafts",
    "[Gmail]/Important",
    "[Gmail]/Sent Mail",
    "[Gmail]/Spam",
    "[Gmail]/Starred",
    "[Gmail]/Trash",
    
    #jmenega3@gmail.com
    #"INBOX",
    #"[Gmail]/All Mail",
    #"[Gmail]/Sent Mail",
    #"[Gmail]/Spam",
    #"[Gmail]/Starred",
    #"[Gmail]/Drafts",
    #"[Gmail]/Trash",
    #"facul"
    # silvia.investur@gmail.com
    "INBOX",
    "[Gmail]",
    "[Gmail]/Com estrela",
    "[Gmail]/Emails enviados",
    "[Gmail]/Importante",
    "[Gmail]/Lixeira",
    "[Gmail]/Rascunhos",
    "[Gmail]/Spam",
    "[Gmail]/Todos os e-mails",
    "Operadora JAPAN"
]

def conectar_gmail(email, senha):
    """Estabelece conexão com o servidor IMAP do Gmail."""
    try:
        print(f"\nTrying to connect: {email}")  # Debug line
        if not email or not senha:
            print(f"❌ Missing credentials for: {email}")  # Debug line
            return None
            
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, timeout=FETCH_TIMEOUT)
        mail.login(email, senha)
        print(f"\n{'='*50}")
        print(f"✅ Connected to Gmail: {email}")
        print(f"{'='*50}")
        return mail
    except (socket.timeout, ssl.SSLError, imaplib.IMAP4.abort) as e:
        print(f"\n{'='*50}")
        print(f"❌ Connection timeout: {email}")
        print(f"Error details: {e}")
        print(f"{'='*50}")
        time.sleep(RETRY_DELAY)
        return None
    except Exception as e:
        print(f"\n{'='*50}")
        print(f"❌ Error connecting to: {email}")
        print(f"Error details: {e}")
        print(f"{'='*50}")
        return None

def listar_pastas(mail):
    """Lista todas as pastas disponíveis na conta."""
    try:
        status, pastas = mail.list()
        if status == "OK":
            return [p.decode().split('"')[-2] for p in pastas if b'"/"' in p]
        return []
    except Exception as e:
        print(f"\n{'='*50}")
        print(f"❌ Error listing folders")
        print(f"Error details: {e}")
        print(f"{'='*50}")
        return []

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

        # Barra de contagem de pastas 
        total_pastas = len([p for p in PASTAS if p.strip('"') in pastas])
        total_pastas += len([p for p in pastas if p not in [p.strip('"') for p in PASTAS]])

        with tqdm(total=total_pastas, desc="Total Progress", position=0) as pbar:
            # Primeiro limpa as pastas prioritárias
            for pasta in PASTAS:
                if pasta.strip('"') in pastas:
                    limpar_pasta(mail, pasta)
                    pbar.update(1)

            # Depois limpa todas as outras pastas
            for pasta in pastas:
                if pasta not in [p.strip('"') for p in PASTAS]:
                    limpar_pasta(mail, pasta)
                    pbar.update(1)

    finally:
        mail.close()
        mail.logout()
        print(f"\n[🎉] LIMPEZA TOTAL CONCLUÍDA PARA {email}!")
        print("[❗] Verifique sua conta para confirmar.")

def limpar_pasta(mail, pasta, email):
    try:
        print(f"\n[📁] Processando pasta: {pasta}")
        
        # Mapear as pastas 
        try:
            # pegar o primeiro item da lista de pastas do gmail
            status, folder_list = mail.list()
            if status != "OK":
                print(f"[-] Erro ao listar pastas")
                return
                
            # Procurar pelo nome correto da pasta
            folder_name = None
            for folder in folder_list:
                folder_decoded = folder.decode()
                if pasta.replace('"', '') in folder_decoded:
                    folder_name = folder_decoded.split('"/"')[-1].strip('"').strip()
                    break
            
            if not folder_name:
                folder_name = pasta
            
            # Selecionar pasta
            status, _ = mail.select(folder_name, readonly=False)
            if status != "OK":
                print(f"[-] Não foi possível acessar a pasta '{pasta}'")
                return
                
        except Exception as e:
            print(f"[-] Erro ao selecionar pasta '{pasta}': {e}")
            return

        # Procurar por todas as pastads da datacorte
        try:
            status, data = mail.search(None, 'ALL')
            if status != "OK":
                print(f"[-] Erro ao buscar e-mails em '{pasta}'")
                return

            email_ids = data[0].split()
            total_emails = len(email_ids)
            
            if total_emails == 0:
                print(f"[!] Nenhum e-mail encontrado em '{pasta}'")
                return

            print(f"[🔍] Encontrados {total_emails} e-mail(s) para limpar em '{pasta}'")
            
            # processar em pequenasbatches
            batch_size = 100
            deleted_count = 0
            
            for i in range(0, total_emails, batch_size):
                batch = email_ids[i:i + batch_size]
                batch_ids = ','.join(email_id.decode() if isinstance(email_id, bytes) else str(email_id) for email_id in batch)
                
                try:
                    
                    # Progresso display
                    progress = (i + len(batch)) / total_emails
                    bar_length = 40
                    filled_length = int(bar_length * progress)
                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                    
                    print(f'\r[{bar}] {i + len(batch)}/{total_emails} ({progress*100:.1f}%) | '
                          f'Deletando...', end='', flush=True)
                    
                except Exception as e:
                    print(f"\n[-] Erro ao processar lote: {e}")
                    continue

            print(f"\n[✔] {deleted_count} e-mail(s) excluído(s) permanentemente de '{pasta}'")
            
        except Exception as e:
            print(f"\n[-] Erro ao processar emails: {e}")
            
    except Exception as e:
        print(f"\n[-] Erro geral ao limpar pasta '{pasta}': {e}")    
def detectar_encoding(texto_bruto):
    """Detecta automaticamente a codificação do texto."""
    resultado = chardet.detect(texto_bruto)
    return resultado["encoding"] if resultado["confidence"] > 0.5 else "utf-8"


def limpar_texto(texto):
    """Remove caracteres estranhos e normaliza o texto."""
    if not texto:
        return ""
    texto = re.sub(r"=\n", "", texto)  # Remove quebras de linha forçadas
    texto = re.sub(r"=[A-F0-9]{2}", "", texto)  # Remove caracteres codificados errados
    return texto.strip()

def clean_filename(name):
    """Clean filename from invalid characters"""
    # Remove um caractere problematico
    name = str(name)
    
    # Remove e escapa qualquer tipo de caractere especial
    name = re.sub(r'\x1b[^m]*m', '', name)
    name = re.sub(r'\x1b[$()][\w@]', '', name)
    name = re.sub(r'[\x00-\x1f\x7f-\xff]', '', name)
    
    # Reescreve qualquer tipo de arquivo com underscores
    name = re.sub(r'[<>:"/\\|?*\r\n\t@\[\]]', '_', name)  # Added [ and ]
    name = re.sub(r'[_ ]+', '_', name)  # Replace multiple underscores/spaces with single underscore
    name = re.sub(r'[.]', '_', name)  # Replace dots with underscores
    
    # Sinalizasao adicional
    name = ''.join(char for char in name if ord(char) < 128)
    name = name.strip('_. ')  # Remove leading/trailing underscores, dots and spaces
    
    # Se o nome for vazio limpar e o usar o padrao 
    if not name or len(name.strip()) == 0:
        name = f"email_{datetime.datetime.now().strftime('%H%M%S')}"
    
    # limite de length de 240 c
    return name[:40]  # Shortened max length to accommodate full pat


def extrair_corpo_email(email_msg):
    """Extrai e decodifica corretamente o corpo do email."""
    corpo = []
    
    if email_msg.is_multipart():
        for parte in email_msg.walk():
            if parte.get_content_type() in ["text/plain", "text/html"]:
                corpo_bruto = parte.get_payload(decode=True)
                try:
                    encoding = parte.get_content_charset() or detectar_encoding(corpo_bruto)
                    texto = corpo_bruto.decode(encoding, errors='replace')
                    corpo.append(limpar_texto(texto))
                except Exception:
                    continue
    else:
        corpo_bruto = email_msg.get_payload(decode=True)
        try:
            encoding = email_msg.get_content_charset() or detectar_encoding(corpo_bruto)
            texto = corpo_bruto.decode(encoding, errors='replace')
            corpo.append(limpar_texto(texto))
        except Exception:
            pass
    
    return "\n\n".join(filter(None, corpo)) or "Erro ao extrair corpo do email"

def get_email_filename(email_msg):
    """Creates a meaningful filename from email subject and date"""
    try:
        # Pegar e limpar
        subject = decode_header(email_msg['Subject'])[0][0]
        if isinstance(subject, bytes):
            try:
                subject = subject.decode('utf-8')
            except UnicodeDecodeError:
                subject = subject.decode('latin-1', errors='replace')
        elif subject is None:
            subject = "No Subject"
        
        # Pegar e limpar uma data
        date_str = email_msg['Date']
        if date_str:
            try:
                # Convert email date to datetime object
                from email.utils import parsedate_to_datetime
                date_obj = parsedate_to_datetime(date_str)
                date_str = date_obj.strftime("%Y-%m-%d_%H-%M-%S")
            except:
                date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        else:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        
        # Clean subject
        clean_subject = clean_filename(subject)
        
        return f"{date_str}_{clean_subject}"
    except Exception as e:
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_no_subject")


def salvar_anexos(email_msg, pasta_backup, email_filename):
    """Salva anexos e imagens do email."""
    for part in email_msg.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        
        # Check for both attachments and inline images
        filename = part.get_filename()
        content_type = part.get_content_type()
        content_id = part.get('Content-ID', '')
        
        # Process if it's an attachment or image
        if filename or content_type.startswith('image/'):
            try:
                # Get or generate filename
                if not filename:
                    # Generate filename for inline images
                    ext = content_type.split('/')[-1]
                    filename = f"inline_image_{datetime.datetime.now().strftime('%H%M%S')}.{ext}"
                
                # Decode filename if needed
                if filename:
                    decoded_parts = decode_header(filename)
                    if decoded_parts[0][1]:
                        filename = decoded_parts[0][0].decode(decoded_parts[0][1])
                    elif isinstance(decoded_parts[0][0], bytes):
                        filename = decoded_parts[0][0].decode('utf-8', errors='replace')
                
                # Clean attachment filename
                clean_name = clean_filename(filename)
                if not clean_name:
                    clean_name = f"attachment_{datetime.datetime.now().strftime('%H%M%S')}"
                
                # Get payload and check if it's not None
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                
                # Create attachments subfolder
                attachments_folder = os.path.join(pasta_backup, 'attachments')
                os.makedirs(attachments_folder, exist_ok=True)
                
                # Save file with content type prefix for better organization
                prefix = 'img_' if content_type.startswith('image/') else 'att_'
                final_filename = f"{prefix}{clean_name}"
                filepath = os.path.join(attachments_folder, final_filename)
                
                with open(filepath, 'wb') as f:
                    f.write(payload)
                    
            except Exception as e:
                print(f"[-] Erro ao salvar anexo {filename if filename else 'unknown'}: {str(e)}")
                continue

def fazer_backup(email, senha):
    mail = conectar_gmail(email, senha)
    if not mail:
        return
    
    try:
        print(f"\n{'='*50}")
        print(f"📂 Starting backup for: {email}")
        print(f"{'='*50}")

        # Create main backup directory for this email
        email_backup_dir = os.path.join(BACKUP_DIR, email)
        os.makedirs(email_backup_dir, exist_ok=True)

        # Process each folder
        with tqdm(total=len(PASTAS), desc=f"📁 Processado pastas:", position=0) as folder_pbar:
            for pasta in PASTAS:
                try:
                    # Properly encode folder name for IMAP
                    pasta_encoded = f'"{pasta}"'.encode('utf-8') if ' ' in pasta or '[' in pasta else pasta.encode('utf-8')
                    status, _ = mail.select(pasta_encoded)  # Fixed duplicate line and indentation
                    if status != "OK":
                        print(f"\n⚠️  Pulando pasta: {pasta}")
                        folder_pbar.update(1)
                        continue

                    # Search for older emails
                    search_criteria = f'BEFORE "{DATA_CORTE}"'.encode('utf-8')
                    status, messages = mail.uid('SEARCH', None, search_criteria)
                    
                    if status != "OK":
                        print(f"\n❌ Error searching in: {pasta}")
                        folder_pbar.update(1)
                        continue

                    emails_ids = messages[0].split()
                    total_emails = len(emails_ids)
                    
                    if total_emails == 0:
                        print(f"\nℹ️  Sem emails na pasta: {pasta}")
                        folder_pbar.update(1)
                        continue

                    print(f"\n📥 Processando {total_emails} emails em: {pasta}")
                    pasta_backup = os.path.join(BACKUP_DIR, email, pasta.replace('/', '_'))
                    os.makedirs(pasta_backup, exist_ok=True)

                    with tqdm(total=total_emails, desc=f"Backing up", position=1, leave=False) as email_pbar:
                        for i in range(0, len(emails_ids), BATCH_SIZE):
                            batch = emails_ids[i:i + BATCH_SIZE]
                            
                            for email_id in batch:
                                for retry in range(MAX_RETRIES):
                                    try:
                                        # Refresh connection if needed
                                        if retry > 0:
                                            mail = conectar_gmail(email, senha)
                                            mail.select(pasta_encoded)
                                        
                                        mail.socket().settimeout(FETCH_TIMEOUT)
                                        
                                        # Fetch in smaller chunks
                                        status, header_data = mail.uid('FETCH', email_id, '(BODY.PEEK[HEADER])')
                                        if status != "OK" or not header_data[0]:
                                            raise Exception("Failed to fetch headers")
                                        
                                        time.sleep(0.5)  # Small pause between fetches
                                        
                                        status, data = mail.uid('FETCH', email_id, '(RFC822)')
                                        if status != "OK" or not data[0]:
                                            raise Exception("Failed to fetch message")
                                        
                                        raw_email = data[0][1]
                                        email_msg = message_from_bytes(raw_email)
                                        email_filename = get_email_filename(email_msg)

                                        # Create folder for email and its attachments
                                        email_folder = os.path.join(pasta_backup, email_filename)
                                        os.makedirs(email_folder, exist_ok=True)
                                        
                                        # Save email in the same folder
                                        # When saving email content, update encoding handling:
                                        with open(os.path.join(email_folder, f"email.eml"), "wb") as f:
                                            f.write(raw_email)
                                            
                                            # Handle subject encoding
                                            subject_parts = decode_header(email_msg['Subject'])
                                            subject = ""
                                            for part, charset in subject_parts:
                                                if isinstance(part, bytes):
                                                    try:
                                                        if charset:
                                                            subject += part.decode(charset)
                                                        else:
                                                            subject += part.decode('utf-8', errors='replace')
                                                    except:
                                                        subject += part.decode('latin-1', errors='replace')
                                                else:
                                                    subject += str(part)
                                            
                                            f.write(f"\nAssunto: {subject}\n".encode('utf-8', errors='replace'))
                                            f.write(f"De: {email_msg['From']}\n".encode('utf-8', errors='replace'))
                                            f.write(f"Data: {email_msg['Date']}\n".encode('utf-8', errors='replace'))
                                            f.write("\n".encode('utf-8') + extrair_corpo_email(email_msg).encode('utf-8', errors='replace'))
                                        
                                        # Save attachments in the same folder
                                        salvar_anexos(email_msg, email_folder, "")
                                        
                                        email_pbar.update(1)
                                        break  # Success
                                        
                                    except (socket.error, ssl.SSLError, imaplib.IMAP4.abort) as e:
                                        if retry == MAX_RETRIES - 1:
                                            print(f"\n❌ Connection error with email {email_id}: {str(e)}")
                                            print(f"   Folder: {pasta}, Email ID: {email_id}")  # Added more detail
                                        time.sleep(RETRY_DELAY * (retry + 1))  # Progressive delay
                                        continue
                                    except Exception as e:
                                        if retry == MAX_RETRIES - 1:
                                            print(f"\n❌ Error with email {email_id}: {str(e)}")
                                            print(f"   Folder: {pasta}, Email ID: {email_id}")  # Added more detail
                                        time.sleep(RETRY_DELAY)
                                        continue
                                        
                            # Small delay between batches
                            time.sleep(0.1)
                    
                    folder_pbar.update(1)

                except Exception as e:
                    print(f"\n❌ Error in folder {pasta}: {str(e)}")
                    folder_pbar.update(1)
                    continue

    finally:
        mail.logout()
        print(f"\n{'='*50}")
        print(f"✅ Backup completed for: {email}")
        print(f"{'='*50}\n")

if __name__ == "__main__":
    try:
        # Add debug information
        print("\n Checando as credencias de email:")
        for acc in ACCOUNTS:
            if acc["email"] and acc["senha"]:
                print(f"✓ Found credentials for: {acc['email']}")
            else:
                print(f"✗ falha ao checar ")

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            futures = [executor.submit(fazer_backup, acc["email"], acc["senha"]) 
                     for acc in ACCOUNTS if acc["email"] and acc["senha"]]
            done, not_done = concurrent.futures.wait(futures, timeout=FETCH_TIMEOUT * 4)
            
            if not_done:
                print("\n[!] Some backups timed out and were not completed")
                for future in not_done:
                    future.cancel()
    except KeyboardInterrupt:
        print("[!] Interrompido pelo usuário.")
    except Exception as e:
        print(f"[!] Error in main execution: {str(e)}")
    finally:
        print("\n[✓] Backup process completed")

