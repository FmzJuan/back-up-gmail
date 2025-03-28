from email.header import decode_header
import os
import re

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
