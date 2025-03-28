import imaplib
import email
import os

# Configurações
EMAIL = 'juan.investur@gmail.com'
SENHA = 'investur321@'  # ou senha de aplicativo
DIRETORIO_BACKUP = 'C:/Users/juan meneghesso/Desktop/back-up-py'

# Conectar ao Gmail
mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login(EMAIL, SENHA)
mail.select('inbox')

# Buscar todos os e-mails
status, mensagens = mail.search(None, 'ALL')
email_ids = mensagens[0].split()

# Criar diretório de backup se não existir
if not os.path.exists(DIRETORIO_BACKUP):
    os.makedirs(DIRETORIO_BACKUP)

# Fazer backup e excluir e-mails
for e_id in email_ids:
    # Buscar o e-mail
    status, msg_data = mail.fetch(e_id, '(RFC822)')
    msg = email.message_from_bytes(msg_data[0][1])
    
    # Salvar o e-mail em um arquivo
    assunto = msg['subject'].replace('/', '_').replace('\\', '_')  # Limpar o assunto para o nome do arquivo
    with open(os.path.join(DIRETORIO_BACKUP, f'{assunto}.eml'), 'wb') as f:
        f.write(msg_data[0][1])
    
    # Excluir o e-mail
    mail.store(e_id, '+FLAGS', '\\Deleted')

# Permanecer as alterações
mail.expunge()

# Logout
mail.logout()

print("Backup concluído e e-mails excluídos com sucesso!")
