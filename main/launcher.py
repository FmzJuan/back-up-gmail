import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime, timedelta
import configparser
import subprocess

class GmailManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Gerenciador de Gmail")
        self.root.geometry("600x500")
        
        # Load email configurations
        self.load_config()
        
        # Create main frames
        self.create_email_frame()
        self.create_date_frame()
        self.create_action_frame()
        
    def load_config(self):
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                self.emails = {}
                print("Reading .env file...")
                for line in f:
                    if line.strip() and '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key.startswith('EMAIL_'):
                            email_num = key.split('_')[1]
                            value = value.strip().strip('"\'')
                            if value:
                                print(f"Found email: {key} = {value}")
                                self.emails[f"Email {email_num}"] = {"enabled": True, "address": value}
            
            if not self.emails:
                print("No emails found in .env file")
            else:
                print(f"Total emails loaded: {len(self.emails)}")
        except Exception as e:
            print(f"Error loading .env: {e}")
            self.emails = {}
    
    def create_email_frame(self):
        email_frame = ttk.LabelFrame(self.root, text="Seleção de Emails", padding=10)
        email_frame.pack(fill="x", padx=10, pady=5)
        
        # Add a select all option
        self.select_all_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(email_frame, text="Selecionar Todos", 
                       variable=self.select_all_var,
                       command=self.toggle_all_emails).pack(pady=5)
        
        self.email_vars = {}
        for email_name, email_data in self.emails.items():
            var = tk.BooleanVar(value=email_data["enabled"])
            self.email_vars[email_name] = var
            
            frame = ttk.Frame(email_frame)
            frame.pack(fill="x", pady=2)
            
            ttk.Checkbutton(frame, text=f"{email_name}: {email_data['address']}", 
                           variable=var).pack(side="left")
        
        # Add status label
        self.status_label = ttk.Label(email_frame, text="")
        self.status_label.pack(pady=5)
        self.update_email_status()

    def toggle_all_emails(self):
        state = self.select_all_var.get()
        for var in self.email_vars.values():
            var.set(state)
        self.update_email_status()

    def update_email_status(self):
        selected = sum(1 for var in self.email_vars.values() if var.get())
        total = len(self.email_vars)
        self.status_label.config(text=f"Emails selecionados: {selected}/{total}")
    
    def create_date_frame(self):
        date_frame = ttk.LabelFrame(self.root, text="Configuração de Data", padding=10)
        date_frame.pack(fill="x", padx=10, pady=5)
        
        # Date selection
        ttk.Label(date_frame, text="Anos anteriores a serem processados:").pack()
        self.years_var = tk.StringVar(value="2.1")
        ttk.Entry(date_frame, textvariable=self.years_var).pack(pady=5)
        
        # Preview date
        self.preview_label = ttk.Label(date_frame, text="")
        self.preview_label.pack()
        self.update_date_preview()
        
        ttk.Button(date_frame, text="Atualizar Preview", 
                   command=self.update_date_preview).pack(pady=5)
    
    def create_action_frame(self):
        action_frame = ttk.LabelFrame(self.root, text="Ações", padding=10)
        action_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(action_frame, text="Executar Backup", 
                   command=self.run_backup).pack(fill="x", pady=5)
        ttk.Button(action_frame, text="Executar Exclusão", 
                   command=self.run_delete).pack(fill="x", pady=5)
    
    def update_date_preview(self):
        try:
            years = float(self.years_var.get())
            date_cutoff = datetime.now() - timedelta(days=365*years)
            self.preview_label.config(
                text=f"Serão processados emails anteriores a: {date_cutoff.strftime('%d-%b-%Y')}")
        except:
            self.preview_label.config(text="Erro no formato da data")
    
    def save_temp_config(self):
        # Save temporary configuration for the scripts
        config = configparser.ConfigParser()
        config['Settings'] = {
            'years': self.years_var.get(),
            'enabled_emails': ','.join(name for name, var in self.email_vars.items() 
                                     if var.get())
        }
        with open('temp_config.ini', 'w') as f:
            config.write(f)
    
    def run_backup(self):
        self.save_temp_config()
        process = subprocess.Popen('python "BACKUP-V10.py"', 
                                 creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    def run_delete(self):
        self.save_temp_config()
        if messagebox.askyesno("Confirmar Exclusão", 
                              "Tem certeza que deseja executar a exclusão?"):
            process = subprocess.Popen('python "delet-gmail-V3.py"', 
                                     creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == "__main__":
    root = tk.Tk()
    app = GmailManager(root)
    root.mainloop()