import customtkinter as ctk
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURAÇÃO INICIAL ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppTriagem(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração da Janela
        self.title("Sistema Ágil de Triagem v1.2 - Layout Otimizado")
        self.geometry("1000x750") # Um pouco mais largo para acomodar inputs lado a lado
        
        # Variáveis de Controle
        self.lista_defeitos = ["Tela Quebrada", "Não Liga", "Carcaça Danificada", 
                               "Bateria Estufada", "Botão Faltando", "Sem Defeito (OK)",
                               "Conector Quebrado", "Mancha na Tela", "Som Ruim", "Wi-Fi Ruim"]
        
        # Inicializar Banco de Dados
        self.init_db()

        # --- LAYOUT PRINCIPAL (GRID) ---
        self.grid_columnconfigure(0, weight=1)
        # A linha 2 (Defeitos) é a que vai esticar se maximizar a tela
        self.grid_rowconfigure(2, weight=1) 

        # ---------------------------------------------------------
        # 1. CABEÇALHO (INPUTS LADO A LADO)
        # ---------------------------------------------------------
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        
        # Configurar colunas do frame interno para dividir 50%/50%
        self.frame_top.grid_columnconfigure(0, weight=1)
        self.frame_top.grid_columnconfigure(1, weight=1)

        # Coluna 0: Código Interno
        self.lbl_cod = ctk.CTkLabel(self.frame_top, text="1. Código Interno (Bipar):", font=("Arial", 14, "bold"))
        self.lbl_cod.grid(row=0, column=0, sticky="w", padx=10, pady=(10,0))
        
        self.entry_cod = ctk.CTkEntry(self.frame_top, placeholder_text="Bipe aqui...", height=40, font=("Arial", 16))
        self.entry_cod.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.entry_cod.bind('<Return>', self.focar_serial) 

        # Coluna 1: Número de Série
        self.lbl_sn = ctk.CTkLabel(self.frame_top, text="2. Número de Série (Opcional):", font=("Arial", 14, "bold"))
        self.lbl_sn.grid(row=0, column=1, sticky="w", padx=10, pady=(10,0))
        
        self.entry_sn = ctk.CTkEntry(self.frame_top, placeholder_text="S/N ou vazio", height=40, font=("Arial", 16))
        self.entry_sn.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 10))
        self.entry_sn.bind('<Return>', lambda event: self.lbl_status.configure(text="Selecione o defeito abaixo 👇", text_color="yellow"))

        # ---------------------------------------------------------
        # 2. ÁREA DE DEFEITOS (EXPANDIDA)
        # ---------------------------------------------------------
        self.lbl_def = ctk.CTkLabel(self, text="3. Selecione o Defeito:", font=("Arial", 16, "bold"))
        self.lbl_def.grid(row=1, column=0, padx=20, pady=(5,0), sticky="w")

        # Aumentei o height para 350 para caberem muitos botões
        self.scroll_defeitos = ctk.CTkScrollableFrame(self, label_text="Painel de Defeitos", height=350)
        self.scroll_defeitos.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        
        self.carregar_botoes_defeitos()

        # ---------------------------------------------------------
        # 3. ADICIONAR NOVO DEFEITO
        # ---------------------------------------------------------
        self.frame_new = ctk.CTkFrame(self)
        self.frame_new.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        self.entry_novo_defeito = ctk.CTkEntry(self.frame_new, placeholder_text="Novo defeito...", width=200)
        self.entry_novo_defeito.pack(side="left", padx=10, pady=10)
        self.btn_add_defeito = ctk.CTkButton(self.frame_new, text="+ Criar Botão", command=self.adicionar_novo_defeito, fg_color="green")
        self.btn_add_defeito.pack(side="left", padx=10)

        # ---------------------------------------------------------
        # 4. HISTÓRICO (COMPACTADO)
        # ---------------------------------------------------------
        # Reduzi o height para 80
        self.frame_hist = ctk.CTkScrollableFrame(self, label_text="Histórico Recente (Últimos 5)", height=80)
        self.frame_hist.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        
        self.atualizar_lista_recente()

        # ---------------------------------------------------------
        # 5. RODAPÉ
        # ---------------------------------------------------------
        self.frame_bottom = ctk.CTkFrame(self, height=40)
        self.frame_bottom.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        self.lbl_status = ctk.CTkLabel(self.frame_bottom, text="Pronto para iniciar.", font=("Arial", 14))
        self.lbl_status.pack(side="left", padx=20)

        self.btn_export = ctk.CTkButton(self.frame_bottom, text="Exportar Excel", command=self.exportar_dados, fg_color="#E85D04")
        self.btn_export.pack(side="right", padx=20, pady=10)

        # Foco inicial
        self.entry_cod.focus()

    # --- LÓGICA DO SISTEMA ---

    def init_db(self):
        self.conn = sqlite3.connect("dados_triagem.db")
        self.cursor = self.conn.cursor()
        
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
        
        self.cursor.execute('CREATE TABLE IF NOT EXISTS defeitos_lista (nome TEXT UNIQUE)')
        self.conn.commit()

        self.cursor.execute('SELECT nome FROM defeitos_lista')
        db_defeitos = [row[0] for row in self.cursor.fetchall()]
        
        if db_defeitos:
            self.lista_defeitos = db_defeitos
        else:
            for d in self.lista_defeitos:
                try:
                    self.cursor.execute('INSERT INTO defeitos_lista (nome) VALUES (?)', (d,))
                except: pass
            self.conn.commit()

    def focar_serial(self, event):
        if self.entry_cod.get():
            self.entry_sn.focus()

    def carregar_botoes_defeitos(self):
        for widget in self.scroll_defeitos.winfo_children():
            widget.destroy()

        row = 0
        col = 0
        max_cols = 3 # Você pode aumentar isso para 4 se a tela for larga
        
        # Configurar colunas para centralizar ou expandir
        for i in range(max_cols):
            self.scroll_defeitos.grid_columnconfigure(i, weight=1)

        for defeito in self.lista_defeitos:
            btn = ctk.CTkButton(self.scroll_defeitos, text=defeito, 
                                height=50, font=("Arial", 13, "bold"),
                                command=lambda d=defeito: self.registrar_triagem(d))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def adicionar_novo_defeito(self):
        novo = self.entry_novo_defeito.get().strip()
        if novo and novo not in self.lista_defeitos:
            self.lista_defeitos.append(novo)
            try:
                self.cursor.execute('INSERT INTO defeitos_lista (nome) VALUES (?)', (novo,))
                self.conn.commit()
            except: pass
            self.carregar_botoes_defeitos()
            self.entry_novo_defeito.delete(0, 'end')

    def atualizar_lista_recente(self):
        for widget in self.frame_hist.winfo_children():
            widget.destroy()

        self.cursor.execute('SELECT cod_interno, defeito, data_hora FROM triagem ORDER BY id DESC LIMIT 5')
        ultimos = self.cursor.fetchall()

        # Cabeçalho compacto
        lbl_head = ctk.CTkLabel(self.frame_hist, text=f"{'CÓDIGO':<15} | {'DEFEITO':<25} | {'HORA'}", font=("Courier", 12, "bold"))
        lbl_head.pack(anchor="w", padx=10)

        for item in ultimos:
            cod = item[0]
            defeito = item[1]
            hora = item[2].split(' ')[1] 
            
            texto_linha = f"{cod:<15} | {defeito:<25} | {hora}"
            lbl = ctk.CTkLabel(self.frame_hist, text=texto_linha, font=("Courier", 12))
            lbl.pack(anchor="w", padx=10)

    def registrar_triagem(self, defeito_selecionado):
        codigo = self.entry_cod.get().strip()
        serial = self.entry_sn.get().strip()

        if not codigo:
            self.lbl_status.configure(text="ERRO: Bipe o código interno!", text_color="red")
            self.entry_cod.focus()
            return

        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.cursor.execute('''
            INSERT INTO triagem (cod_interno, num_serie, defeito, data_hora, sync_status)
            VALUES (?, ?, ?, ?, 0)
        ''', (codigo, serial, defeito_selecionado, data_hora))
        self.conn.commit()

        msg = f"SALVO: {codigo} -> {defeito_selecionado}"
        self.lbl_status.configure(text=msg, text_color="#00FF00")

        self.atualizar_lista_recente()

        self.entry_cod.delete(0, 'end')
        self.entry_sn.delete(0, 'end')
        self.entry_cod.focus()

    def exportar_dados(self):
        try:
            query = "SELECT * FROM triagem"
            df = pd.read_sql_query(query, self.conn)
            
            nome_arquivo = f"triagem_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(nome_arquivo, index=False)
            
            self.lbl_status.configure(text=f"Exportado: {nome_arquivo}", text_color="#00FFFF")
            os.system(f"start {nome_arquivo}") 
        except Exception as e:
            self.lbl_status.configure(text=f"Erro ao exportar: {e}", text_color="red")

if __name__ == "__main__":
    app = AppTriagem()
    app.mainloop()