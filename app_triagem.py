import customtkinter as ctk
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURAÇÃO INICIAL ---
ctk.set_appearance_mode("Dark")  # Modos: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")

class AppTriagem(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração da Janela
        self.title("Sistema Ágil de Triagem v1.0")
        self.geometry("900x600")
        
        # Variáveis de Controle
        self.lista_defeitos = ["Tela Quebrada", "Não Liga", "Carcaça Danificada", 
                               "Bateria Estufada", "Botão Faltando", "Sem Defeito (OK)"]
        
        # Inicializar Banco de Dados
        self.init_db()

        # --- LAYOUT ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # A área dos botões vai expandir

        # 1. Cabeçalho e Inputs
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        # Input: Código Interno
        self.lbl_cod = ctk.CTkLabel(self.frame_top, text="1. Código Interno (Bipar):", font=("Arial", 14, "bold"))
        self.lbl_cod.pack(anchor="w", padx=10)
        self.entry_cod = ctk.CTkEntry(self.frame_top, placeholder_text="Bipe aqui...", height=40, font=("Arial", 16))
        self.entry_cod.pack(fill="x", padx=10, pady=(0, 10))
        self.entry_cod.bind('<Return>', self.focar_serial) # Ao dar Enter, pula pro próximo

        # Input: Número de Série
        self.lbl_sn = ctk.CTkLabel(self.frame_top, text="2. Número de Série (Opcional):", font=("Arial", 14, "bold"))
        self.lbl_sn.pack(anchor="w", padx=10)
        self.entry_sn = ctk.CTkEntry(self.frame_top, placeholder_text="S/N ou vazio", height=40, font=("Arial", 16))
        self.entry_sn.pack(fill="x", padx=10, pady=(0, 10))
        self.entry_sn.bind('<Return>', lambda event: self.lbl_status.configure(text="Selecione o defeito abaixo 👇", text_color="yellow"))

        # 2. Área de Defeitos (Botões)
        self.lbl_def = ctk.CTkLabel(self, text="3. Selecione o Defeito (Clique para Salvar):", font=("Arial", 16, "bold"))
        self.lbl_def.grid(row=1, column=0, padx=20, pady=(10,0), sticky="w")

        self.scroll_defeitos = ctk.CTkScrollableFrame(self, label_text="Lista de Defeitos")
        self.scroll_defeitos.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        
        # Carregar botões
        self.carregar_botoes_defeitos()

        # 3. Adicionar Novo Defeito Rápido
        self.frame_new = ctk.CTkFrame(self)
        self.frame_new.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.entry_novo_defeito = ctk.CTkEntry(self.frame_new, placeholder_text="Novo defeito...", width=200)
        self.entry_novo_defeito.pack(side="left", padx=10, pady=10)
        
        self.btn_add_defeito = ctk.CTkButton(self.frame_new, text="+ Adicionar", command=self.adicionar_novo_defeito, fg_color="green")
        self.btn_add_defeito.pack(side="left", padx=10)

        # 4. Rodapé e Ações
        self.frame_bottom = ctk.CTkFrame(self, height=100)
        self.frame_bottom.grid(row=4, column=0, padx=20, pady=20, sticky="ew")

        self.lbl_status = ctk.CTkLabel(self.frame_bottom, text="Aguardando início...", font=("Arial", 14))
        self.lbl_status.pack(side="left", padx=20)

        self.btn_export = ctk.CTkButton(self.frame_bottom, text="Exportar Excel (.xlsx)", command=self.exportar_dados, fg_color="#E85D04")
        self.btn_export.pack(side="right", padx=20, pady=20)

        # Foco inicial
        self.entry_cod.focus()

    # --- LÓGICA DO SISTEMA ---

    def init_db(self):
        """Cria a tabela se não existir e carrega defeitos salvos"""
        self.conn = sqlite3.connect("dados_triagem.db")
        self.cursor = self.conn.cursor()
        
        # Tabela de Triagem
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS triagem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cod_interno TEXT NOT NULL,
                num_serie TEXT,
                defeito TEXT NOT NULL,
                data_hora TEXT,
                sync_status INTEGER DEFAULT 0
            )
        ''')
        
        # Tabela de Defeitos (para salvar novos tipos)
        self.cursor.execute('CREATE TABLE IF NOT EXISTS defeitos_lista (nome TEXT UNIQUE)')
        self.conn.commit()

        # Carregar defeitos do banco ou usar os padrões
        self.cursor.execute('SELECT nome FROM defeitos_lista')
        db_defeitos = [row[0] for row in self.cursor.fetchall()]
        
        if db_defeitos:
            self.lista_defeitos = db_defeitos
        else:
            # Se vazio, insere os padrões
            for d in self.lista_defeitos:
                try:
                    self.cursor.execute('INSERT INTO defeitos_lista (nome) VALUES (?)', (d,))
                except: pass
            self.conn.commit()

    def focar_serial(self, event):
        """Pula do campo Código para o Serial"""
        if self.entry_cod.get():
            self.entry_sn.focus()

    def carregar_botoes_defeitos(self):
        """Gera os botões na tela dinamicamente"""
        # Limpar botões antigos
        for widget in self.scroll_defeitos.winfo_children():
            widget.destroy()

        # Criar grid de botões
        row = 0
        col = 0
        max_cols = 3 # Quantos botões por linha
        
        for defeito in self.lista_defeitos:
            btn = ctk.CTkButton(self.scroll_defeitos, text=defeito, 
                                height=50, font=("Arial", 14, "bold"),
                                command=lambda d=defeito: self.registrar_triagem(d))
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def adicionar_novo_defeito(self):
        """Adiciona um novo defeito à lista e ao banco"""
        novo = self.entry_novo_defeito.get().strip()
        if novo and novo not in self.lista_defeitos:
            self.lista_defeitos.append(novo)
            self.cursor.execute('INSERT INTO defeitos_lista (nome) VALUES (?)', (novo,))
            self.conn.commit()
            self.carregar_botoes_defeitos() # Recarrega a tela
            self.entry_novo_defeito.delete(0, 'end')

    def registrar_triagem(self, defeito_selecionado):
        """O CORAÇÃO DO APP: Salva e reseta"""
        codigo = self.entry_cod.get().strip()
        serial = self.entry_sn.get().strip()

        if not codigo:
            self.lbl_status.configure(text="ERRO: Bipe o código interno!", text_color="red")
            self.entry_cod.focus()
            return

        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Salvar no SQLite
        self.cursor.execute('''
            INSERT INTO triagem (cod_interno, num_serie, defeito, data_hora, sync_status)
            VALUES (?, ?, ?, ?, 0)
        ''', (codigo, serial, defeito_selecionado, data_hora))
        self.conn.commit()

        # Feedback Visual
        msg = f"SALVO: {codigo} | {defeito_selecionado}"
        self.lbl_status.configure(text=msg, text_color="#00FF00")

        # Limpar e Focar no Início (Agilidade Máxima)
        self.entry_cod.delete(0, 'end')
        self.entry_sn.delete(0, 'end')
        self.entry_cod.focus()

    def exportar_dados(self):
        """Usa Pandas para exportar tudo para Excel"""
        try:
            query = "SELECT * FROM triagem"
            df = pd.read_sql_query(query, self.conn)
            
            nome_arquivo = f"triagem_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(nome_arquivo, index=False)
            
            self.lbl_status.configure(text=f"Exportado: {nome_arquivo}", text_color="#00FFFF")
            os.system(f"start {nome_arquivo}") # Abre o arquivo (Windows)
        except Exception as e:
            self.lbl_status.configure(text=f"Erro ao exportar: {e}", text_color="red")

if __name__ == "__main__":
    app = AppTriagem()
    app.mainloop()