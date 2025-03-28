from datetime import datetime, timedelta

# Função para calcular a data de corte
def calcular_data_corte(anos=2.5):
    """
    Calcula a data de corte, que é a data de 'n' anos atrás.
    Retorna a data no formato 'dd-Mon-yyyy' (padrão IMAP).
    """
    data_corte = datetime.now() - timedelta(days=365*anos)
    return data_corte.strftime("%d-%b-%Y")

# Definir a data de corte (pode ser personalizada aqui)
DATA_CORTE = calcular_data_corte(2.5)
