import customtkinter as ctk
import sqlite3
import pandas as pd
from datetime import datetime
from tkinter import messagebox, ttk, filedialog # ttk para a tabela

# --- CONFIGURAÇÃO INICIAL ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

ICONES_DISPONIVEIS = [
    "📱 Smartphone", "💻 Notebook", "🎧 Fone", "⌚ Smartwatch", 
    "📷 Câmera", "🎮 Console", "📺 TV", "🔌 Acessório", 
    "⌨ Teclado", "🖱 Mouse", "🖨 Impressora", "📟 Tablet"
]

# --- GERENCIADOR DE BANCO DE DADOS ---
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect("sistema_triagem_v3.db")
        self.cursor = self.conn.cursor()
        self.criar_tabelas()

    def criar_tabelas(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                icone TEXT NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS defeitos_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria_id INTEGER,
                nome_defeito TEXT NOT NULL,
                FOREIGN KEY(categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS triagem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria_id INTEGER,
                cod_interno TEXT NOT NULL,
                num_serie TEXT,
                defeito TEXT NOT NULL,
                data_hora TEXT,
                FOREIGN KEY(categoria_id) REFERENCES categorias(id)
            )
        ''')
        self.conn.commit()
        
        self.cursor.execute('SELECT count(*) FROM categorias')
        if self.cursor.fetchone()[0] == 0:
            self.criar_categoria_exemplo("Celular Samsung", "📱", ["Tela Quebrada", "Bateria", "OK"])

    def criar_categoria_exemplo(self, nome, icone, defeitos):
        self.add_categoria(nome, icone, defeitos)

    def get_categorias(self):
        self.cursor.execute('SELECT * FROM categorias')
        return self.cursor.fetchall()

    def get_defeitos(self, cat_id):
        self.cursor.execute('SELECT nome_defeito FROM defeitos_config WHERE categoria_id = ?', (cat_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def add_categoria(self, nome, icone, defeitos_iniciais):
        icone_limpo = icone.split(" ")[0]
        self.cursor.execute('INSERT INTO categorias (nome, icone) VALUES (?, ?)', (nome, icone_limpo))
        cat_id = self.cursor.lastrowid
        for defeito in defeitos_iniciais:
            if defeito.strip():
                self.cursor.execute('INSERT INTO defeitos_config (categoria_id, nome_defeito) VALUES (?, ?)', (cat_id, defeito.strip()))
        self.conn.commit()

    def update_categoria(self, cat_id, novo_nome, novo_icone):
        icone_limpo = novo_icone.split(" ")[0]
        self.cursor.execute('UPDATE categorias SET nome = ?, icone = ? WHERE id = ?', (novo_nome, icone_limpo, cat_id))
        self.conn.commit()

    def add_defeito_single(self, cat_id, nome_defeito):
        self.cursor.execute('INSERT INTO defeitos_config (categoria_id, nome_defeito) VALUES (?, ?)', (cat_id, nome_defeito))
        self.conn.commit()

    def delete_defeito_single(self, cat_id, nome_defeito):
        self.cursor.execute('DELETE FROM defeitos_config WHERE categoria_id = ? AND nome_defeito = ?', (cat_id, nome_defeito))
        self.conn.commit()

    def delete_categoria(self, cat_id):
        self.cursor.execute('DELETE FROM defeitos_config WHERE categoria_id = ?', (cat_id,))
        self.cursor.execute('DELETE FROM categorias WHERE id = ?', (cat_id,))
        self.conn.commit()

    def registrar_triagem(self, cat_id, cod, serial, defeito):
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO triagem (categoria_id, cod_interno, num_serie, defeito, data_hora)
            VALUES (?, ?, ?, ?, ?)
        ''', (cat_id, cod, serial, defeito, data))
        self.conn.commit()

    def get_historico_tabela(self, cat_id):
        self.cursor.execute('''
            SELECT data_hora, cod_interno, num_serie, defeito FROM triagem 
            WHERE categoria_id = ? ORDER BY id DESC LIMIT 50
        ''', (cat_id,))
        return self.cursor.fetchall()

    def exportar_excel(self, cat_id):
        self.cursor.execute('''
            SELECT data_hora, cod_interno, num_serie, defeito FROM triagem 
            WHERE categoria_id = ? ORDER BY id DESC
        ''', (cat_id,))
        dados = self.cursor.fetchall()
        columns = ["Data/Hora", "Código Interno", "Nº Série", "Defeito"]
        return pd.DataFrame(dados, columns=columns)

class HubFrame(ctk.CTkFrame):
    def __init__(self, master, db, callback_abrir_triagem):
        super().__init__(master)
        self.db = db
        self.callback = callback_abrir_triagem
        
        self.lbl_titulo = ctk.CTkLabel(self, text="Hub de Produtos", font=("Arial", 24, "bold"))
        self.lbl_titulo.pack(pady=20)
        self.btn_novo = ctk.CTkButton(self, text="+ Novo Produto", fg_color="green", command=self.abrir_modal_novo)
        self.btn_novo.pack(pady=5)
        self.scroll_cards = ctk.CTkScrollableFrame(self, label_text="Produtos Cadastrados", height=500)
        self.scroll_cards.pack(fill="both", expand=True, padx=20, pady=10)
        self.carregar_cards()

    def carregar_cards(self):
        for widget in self.scroll_cards.winfo_children(): widget.destroy()
        categorias = self.db.get_categorias()
        self.scroll_cards.grid_columnconfigure((0,1,2), weight=1)
        row, col = 0, 0
        for cat in categorias:
            cat_id, nome, icone = cat
            self.criar_card(cat_id, nome, icone, row, col)
            col += 1
            if col > 2: col = 0; row += 1

    def criar_card(self, cat_id, nome, icone, r, c):
        frame_card = ctk.CTkFrame(self.scroll_cards, border_width=2, border_color="#333")
        frame_card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
        
        ctk.CTkButton(frame_card, text="⚙", width=30, height=30, fg_color="transparent", text_color="gray", 
                      command=lambda: self.abrir_modal_config(cat_id, nome, icone)).place(relx=0.85, rely=0.05)
        ctk.CTkLabel(frame_card, text=icone, font=("Arial", 60)).pack(pady=(20, 5))
        ctk.CTkLabel(frame_card, text=nome, font=("Arial", 16, "bold")).pack(pady=5)
        ctk.CTkButton(frame_card, text="Acessar", command=lambda: self.callback(cat_id, nome)).pack(pady=15, padx=20)

    def abrir_modal_novo(self):
        top = ctk.CTkToplevel(self)
        top.title("Cadastrar Produto")
        top.geometry("450x600")
        top.grab_set()
        
        self.novos_defeitos_temp = []
        ctk.CTkLabel(top, text="Nome:").pack(pady=(10, 2))
        entry_nome = ctk.CTkEntry(top, width=300)
        entry_nome.pack(pady=5)
        
        ctk.CTkLabel(top, text="Ícone:").pack(pady=(10, 2))
        menu_icone = ctk.CTkOptionMenu(top, values=ICONES_DISPONIVEIS, width=300)
        menu_icone.pack(pady=5)

        ctk.CTkLabel(top, text="Defeitos:").pack(pady=(20, 2))
        frame_input_def = ctk.CTkFrame(top, fg_color="transparent")
        frame_input_def.pack(pady=5)
        entry_def = ctk.CTkEntry(frame_input_def, width=200)
        entry_def.pack(side="left", padx=5)

        frame_lista = ctk.CTkScrollableFrame(top, height=150, width=300)
        frame_lista.pack(pady=10)

        def refresh_lista_temp():
            for w in frame_lista.winfo_children(): w.destroy()
            for item in self.novos_defeitos_temp:
                f = ctk.CTkFrame(frame_lista, fg_color="transparent")
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f, text=f"• {item}").pack(side="left")
                ctk.CTkButton(f, text="x", width=20, fg_color="red", command=lambda i=item: remove_temp(i)).pack(side="right")
        
        def remove_temp(item):
            self.novos_defeitos_temp.remove(item); refresh_lista_temp()
        
        def add_temp():
            if entry_def.get(): self.novos_defeitos_temp.append(entry_def.get()); entry_def.delete(0,'end'); refresh_lista_temp()
        
        entry_def.bind('<Return>', lambda e: add_temp())
        ctk.CTkButton(frame_input_def, text="+", width=40, command=add_temp).pack(side="left")

        def salvar():
            if entry_nome.get():
                self.db.add_categoria(entry_nome.get(), menu_icone.get(), self.novos_defeitos_temp)
                self.carregar_cards(); top.destroy()
        
        ctk.CTkButton(top, text="Salvar", command=salvar, fg_color="green").pack(pady=20)

    def abrir_modal_config(self, cat_id, nome_atual, icone_atual):
        top = ctk.CTkToplevel(self)
        top.geometry("450x600")
        top.grab_set()
        
        ctk.CTkLabel(top, text="Editar Nome/Ícone").pack(pady=5)
        e_nome = ctk.CTkEntry(top); e_nome.insert(0, nome_atual); e_nome.pack()
        m_icone = ctk.CTkOptionMenu(top, values=ICONES_DISPONIVEIS); m_icone.set(icone_atual); m_icone.pack(pady=5)
        ctk.CTkButton(top, text="Atualizar", command=lambda: [self.db.update_categoria(cat_id, e_nome.get(), m_icone.get()), self.carregar_cards()]).pack(pady=5)
        
        frame_lista = ctk.CTkScrollableFrame(top, height=200)
        frame_lista.pack(fill="x", padx=20)
        
        e_new = ctk.CTkEntry(top, placeholder_text="Novo defeito..."); e_new.pack(pady=5)
        ctk.CTkButton(top, text="Add Defeito", command=lambda: [self.db.add_defeito_single(cat_id, e_new.get()), e_new.delete(0,'end'), recarregar()]).pack()
        ctk.CTkButton(top, text="Excluir Produto", fg_color="red", command=lambda: [self.db.delete_categoria(cat_id), self.carregar_cards(), top.destroy()]).pack(pady=20)

        def recarregar():
            for w in frame_lista.winfo_children(): w.destroy()
            for d in self.db.get_defeitos(cat_id):
                f = ctk.CTkFrame(frame_lista); f.pack(fill="x", pady=2)
                ctk.CTkLabel(f, text=d).pack(side="left")
                ctk.CTkButton(f, text="X", width=30, fg_color="red", command=lambda d=d: [self.db.delete_defeito_single(cat_id, d), recarregar()]).pack(side="right")
        recarregar()
        
       


class TriageFrame(ctk.CTkFrame):
    def __init__(self, master, db, categoria_id, nome_categoria, callback_voltar):
        super().__init__(master)
        self.db = db
        self.cat_id = categoria_id
        self.cat_nome = nome_categoria
        self.callback_voltar = callback_voltar
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=0) 
        self.grid_rowconfigure(5, weight=1) 

        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        
        ctk.CTkButton(frame_header, text="⬅ Voltar", width=80, command=self.callback_voltar, fg_color="#444").pack(side="left")
        ctk.CTkLabel(frame_header, text=f"Triagem: {self.cat_nome}", font=("Arial", 20, "bold")).pack(side="left", padx=20)
        
        btn_export = ctk.CTkButton(frame_header, text="📥 Exportar Excel", fg_color="#1D6F42", command=self.acao_exportar)
        btn_export.pack(side="right")

        self.frame_inputs = ctk.CTkFrame(self)
        self.frame_inputs.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.frame_inputs.grid_columnconfigure((0,1), weight=1)

        ctk.CTkLabel(self.frame_inputs, text="Código Interno:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", padx=10)
        self.entry_cod = ctk.CTkEntry(self.frame_inputs, height=40, placeholder_text="Bipe aqui...", font=("Arial", 14))
        self.entry_cod.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.entry_cod.bind('<Return>', self.focar_serial)

        ctk.CTkLabel(self.frame_inputs, text="Número de Série:", font=("Arial", 12, "bold")).grid(row=0, column=1, sticky="w", padx=10)
        self.entry_sn = ctk.CTkEntry(self.frame_inputs, height=40, placeholder_text="Opcional")
        self.entry_sn.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 10))
        self.entry_sn.bind('<Return>', lambda e: self.lbl_status.configure(text="Selecione o defeito acima ☝", text_color="#FCA311"))

        ctk.CTkLabel(self, text="Selecione o Defeito:", font=("Arial", 14, "bold")).grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.scroll_defeitos = ctk.CTkScrollableFrame(self, height=140, label_text="") 
        self.scroll_defeitos.grid(row=3, column=0, padx=20, pady=5, sticky="ew") # sticky ew apenas, não nsew
        
        self.carregar_botoes_defeitos()

        self.lbl_status = ctk.CTkLabel(self, text="Aguardando...", font=("Arial", 14), text_color="gray")
        self.lbl_status.grid(row=4, column=0, pady=5)

        frame_tabela = ctk.CTkFrame(self, fg_color="transparent")
        frame_tabela.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        ctk.CTkLabel(frame_tabela, text="Histórico Recente (Sessão)", anchor="w").pack(fill="x")
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", 
                        background="#2b2b2b", 
                        foreground="white", 
                        fieldbackground="#2b2b2b", 
                        bordercolor="#2b2b2b",
                        rowheight=25)
        style.configure("Treeview.Heading", 
                        background="#1f1f1f", 
                        foreground="white", 
                        relief="flat")
        style.map("Treeview", background=[('selected', '#1f538d')])

        columns = ("hora", "cod", "sn", "defeito")
        self.tree = ttk.Treeview(frame_tabela, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("hora", text="Hora")
        self.tree.heading("cod", text="Código")
        self.tree.heading("sn", text="Serial")
        self.tree.heading("defeito", text="Defeito Apontado")
        
        self.tree.column("hora", width=100, anchor="center")
        self.tree.column("cod", width=150, anchor="center")
        self.tree.column("sn", width=150, anchor="center")
        self.tree.column("defeito", width=200, anchor="w")

        scrollbar = ctk.CTkScrollbar(frame_tabela, orientation="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.atualizar_tabela()
        self.entry_cod.focus()

    def focar_serial(self, event):
        if self.entry_cod.get(): self.entry_sn.focus()

    def carregar_botoes_defeitos(self):
        defeitos = self.db.get_defeitos(self.cat_id)
        
        cols = 3
        for i in range(cols): self.scroll_defeitos.grid_columnconfigure(i, weight=1)

        row, col = 0, 0
        for defeito in defeitos:
            btn = ctk.CTkButton(self.scroll_defeitos, text=defeito, height=45,
                                font=("Arial", 13, "bold"),
                                fg_color="#3B8ED0", hover_color="#36719F",
                                command=lambda d=defeito: self.registrar(d))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            col += 1
            if col >= cols: col = 0; row += 1

    def registrar(self, defeito):
        cod = self.entry_cod.get().strip()
        sn = self.entry_sn.get().strip()
        
        if not cod:
            self.lbl_status.configure(text="⚠ ERRO: Bipe o Código Interno primeiro!", text_color="#FF5555")
            self.entry_cod.focus()
            return

        self.db.registrar_triagem(self.cat_id, cod, sn, defeito)
        
        self.lbl_status.configure(text=f"✅ Sucesso: {cod} -> {defeito}", text_color="#55FF55")
        self.atualizar_tabela()
        
        self.entry_cod.delete(0, 'end')
        self.entry_sn.delete(0, 'end')
        self.entry_cod.focus()

    def atualizar_tabela(self):
        # Limpar tabela atual
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        dados = self.db.get_historico_tabela(self.cat_id)
        for row in dados:
            # row = (data_hora, cod, sn, defeito)
            hora_formatada = row[0].split(' ')[1] # Pega só o HH:MM:SS
            self.tree.insert("", "end", values=(hora_formatada, row[1], row[2], row[3]))

    def acao_exportar(self):
        df = self.db.exportar_excel(self.cat_id)
        if df.empty:
            messagebox.showinfo("Vazio", "Não há dados para exportar.")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=f"Relatorio_{self.cat_nome}_{datetime.now().strftime('%Y%m%d')}"
        )
        
        if filename:
            try:
                df.to_excel(filename, index=False)
                messagebox.showinfo("Sucesso", "Relatório exportado com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar: {e}")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema Ágil de Triagem v3.0")
        self.geometry("1100x850")
        
        self.db = DatabaseManager()
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.mostrar_hub()

    def mostrar_hub(self):
        for w in self.container.winfo_children(): w.destroy()
        HubFrame(self.container, self.db, self.mostrar_triagem).pack(fill="both", expand=True)

    def mostrar_triagem(self, cat_id, nome_cat):
        for w in self.container.winfo_children(): w.destroy()
        TriageFrame(self.container, self.db, cat_id, nome_cat, self.mostrar_hub).pack(fill="both", expand=True)

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()