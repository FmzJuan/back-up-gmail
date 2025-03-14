import imaplib

ImapPort = 993
# Conectar ao servidor IMAP do Gmail
mail = imaplib.IMAP4_SSL('imap.gmail.com')

# Fazer login
mail.login('juan.investur@gmail.com', 'uurz jwiz bzjy sbbk')

# Selecionar a caixa de entrada
mail.select('inbox')

# Buscar e-mails
status, messages = mail.search(None, 'ALL')
print(messages)

# Logout
mail.logout()
