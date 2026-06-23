from tkinter import *
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import time
import os
import json

# Nome do arquivo de banco de dados
JSON_FILE = "componentes.json"
arduino = None
componentes_carregados = {}  # Dicionário para guardar os dados dos componentes

def inicializar_json():
    """Cria o arquivo JSON com uma estrutura vazia se ele não existir."""
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, mode='w', encoding='utf-8') as f:
            json.dump({}, f, indent=4)
        # Inserir o RC522 como padrão inicial para facilitar
        salvar_componente_json("RC522", "0x37", "0x91,0x92")

def salvar_componente_json(nome, handshake, sucessos):
    """Carrega o JSON atual, adiciona o novo componente e salva de volta."""
    dados = {}
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, mode='r', encoding='utf-8') as f:
                dados = json.load(f)
        except json.JSONDecodeError:
            dados = {}
            
    # Adiciona ou atualiza o componente no dicionário
    dados[nome] = {
        "Handshake": handshake,
        "Sucessos": sucessos
    }
    
    with open(JSON_FILE, mode='w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_componentes():
    """Lê o JSON e atualiza o dicionário global e o Combobox."""
    global componentes_carregados
    componentes_carregados.clear()
    
    if not os.path.exists(JSON_FILE):
        inicializar_json()
        
    try:
        with open(JSON_FILE, mode='r', encoding='utf-8') as f:
            dados = json.load(f)
            for nome, info in dados.items():
                componentes_carregados[nome] = {
                    "handshake": info["Handshake"],
                    "sucessos": [s.strip() for s in info["Sucessos"].split(",")]
                }
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao ler o arquivo JSON: {e}")
            
    # Atualiza o combobox de seleção
    nomes = list(componentes_carregados.keys())
    combo_componentes['values'] = nomes
    if nomes:
        combo_componentes.current(0)

def cadastrar_novo_componente():
    nome = entry_nome.get().strip()
    handshake = entry_handshake.get().strip()
    sucessos = entry_sucessos.get().strip()
    
    if not nome or not handshake or not sucessos:
        messagebox.showwarning("Aviso", "Todos os campos de cadastro são obrigatórios!")
        return
        
    if nome in componentes_carregados:
        messagebox.showwarning("Aviso", "Já existe um componente com este nome!")
        return

    try:
        # Validação simples de formato (garantir que são inteiros ou hexadecimais válidos)
        int(handshake, 16) if '0x' in handshake else int(handshake)
        for s in sucessos.split(','):
            int(s.strip(), 16) if '0x' in s.strip() else int(s.strip())
    except ValueError:
        messagebox.showerror("Erro", "Os endereços de Handshake e Sucesso devem ser inteiros ou hexadecimais (ex: 0x37)!")
        return

    salvar_componente_json(nome, handshake, sucessos)
    carregar_componentes() # Recarrega a lista
    
    # Limpa os campos de texto
    entry_nome.delete(0, END)
    entry_handshake.delete(0, END)
    entry_sucessos.delete(0, END)
    messagebox.showinfo("Sucesso", f"Componente '{nome}' cadastrado com sucesso!")

def atualizar_portas():
    portas = serial.tools.list_ports.comports()
    lista_portas = [porta.device for porta in portas]
    
    combo_portas['values'] = lista_portas
    if lista_portas:
        combo_portas.current(0)
        texto_status.config(text="Portas atualizadas.")
    else:
        combo_portas.set('')
        texto_status.config(text="Nenhuma porta encontrada!")

def conectar_arduino():
    global arduino
    porta_selecionada = combo_portas.get()
    
    if not porta_selecionada:
        messagebox.showwarning("Aviso", "Selecione uma porta!")
        return

    if arduino and arduino.is_open:
        arduino.close()

    try:
        arduino = serial.Serial(porta_selecionada, 9600, timeout=1)
        texto_status.config(text=f"Conectado em {porta_selecionada}")
        time.sleep(2)
        botao_acao.config(state="normal")
    except Exception as e:
        texto_status.config(text="Erro ao conectar!")
        messagebox.showerror("Erro", f"Não foi possível conectar à porta {porta_selecionada}.\n{e}")
        botao_acao.config(state="disabled")

def envia_teste():
    if not arduino or not arduino.is_open:
        messagebox.showerror("Erro", "O arduino não está conectado")
        return
    
    comp_selecionado = combo_componentes.get()
    if not comp_selecionado:
        messagebox.showerror("Erro", "Nenhum componente selecionado!")
        return
        
    # Obtém as especificações do componente vindas do JSON
    dados_comp = componentes_carregados[comp_selecionado]
    valor_digitado = dados_comp["handshake"]
    
    try:
        byte_com_conversao = int(valor_digitado, 16) if '0x' in valor_digitado else int(valor_digitado)
        arduino.write(bytes([byte_com_conversao]))
    
        texto_resultado.config(text="Aguardando resposta...")
        raiz.update_idletasks()

        resposta_bruta = arduino.read(1)
        if resposta_bruta:
            valor_retornado = resposta_bruta[0]
            status_msg = f"Resposta: 0x{valor_retornado:02X} - "
            
            # Converte a lista de sucessos salvas em inteiros para comparação direta
            lista_sucessos_int = []
            for s in dados_comp["sucessos"]:
                num = int(s, 16) if '0x' in s else int(s)
                lista_sucessos_int.append(num)
                
            # Validação dinâmica baseada no componente
            if valor_retornado in [0x00, 0xFF]:
                status_msg += f"Erro físico no dispositivo."
            elif valor_retornado in lista_sucessos_int:
                status_msg += f"Sucesso! {comp_selecionado} OK."
            else:
                status_msg += "Resposta desconhecida."
             
            texto_resultado.config(text=status_msg)
        else:
            texto_resultado.config(text="Erro: Sem resposta (Timeout).")
            messagebox.showerror("Timeout", "O Arduino não respondeu dentro do tempo limite.")
    
    except ValueError:
        messagebox.showerror("Erro", "Erro ao processar os dados hexadecimais do componente.")
    
def ao_fechar():
    if arduino and arduino.is_open:
        arduino.close()
    raiz.destroy()

# --- INTERFACE GRÁFICA ---
raiz = Tk()
raiz.title("Gerenciador de Componentes & Arduino")
raiz.geometry("800x500")

# Inicializa o mainframe com Grid para separar em colunas
mainframe = ttk.Frame(raiz, padding="20")
mainframe.pack(fill=BOTH, expand=True)

# Configuração de weights de colunas para dar espaço proporcional
mainframe.columnconfigure(0, weight=1) # Lado Esquerdo/Meio (Operação)
mainframe.columnconfigure(1, weight=1) # Lado Direito (Cadastro)

frame_esquerda = ttk.Frame(mainframe)
frame_esquerda.grid(row=0, column=0, sticky="nsew", padx=10)

# 1. Conexão
frame_conexao = ttk.Labelframe(frame_esquerda, text="Conexão", padding="10")
frame_conexao.pack(fill="x", pady=5)

texto_conexao = ttk.Label(frame_conexao, text="Selecionar porta:")
texto_conexao.pack(anchor="w")

combo_portas = ttk.Combobox(frame_conexao, state="readonly")
combo_portas.pack(fill="x", pady=5)

frame_botoes_conexao = ttk.Frame(frame_conexao)
frame_botoes_conexao.pack(fill="x", pady=2)

botao_atualizar = ttk.Button(frame_botoes_conexao, text="Atualizar Portas", command=atualizar_portas)
botao_atualizar.pack(side=LEFT, expand=True, fill="x", padx=(0, 2))

botao_conectar = ttk.Button(frame_botoes_conexao, text="Conectar", command=conectar_arduino)
botao_conectar.pack(side=LEFT, expand=True, fill="x", padx=(2, 0))

texto_status = ttk.Label(frame_conexao, text="Não conectado", foreground="gray")
texto_status.pack(pady=5)


# 2. Seleção de Componente
frame_config = ttk.Labelframe(frame_esquerda, text="Componente Alvo", padding="10")
frame_config.pack(fill="x", pady=5)

texto_config = ttk.Label(frame_config, text="Selecione o componente cadastrado:")
texto_config.pack(anchor="w")

combo_componentes = ttk.Combobox(frame_config, state="readonly")
combo_componentes.pack(fill="x", pady=5)


# 3. Execução da Ação
frame_acao = ttk.Labelframe(frame_esquerda, text="Ação", padding="10")
frame_acao.pack(fill="x", pady=5)

texto_acao = ttk.Label(frame_acao, text="Enviar endereço de handshake para o Arduino:")
texto_acao.pack(anchor="w")

botao_acao = ttk.Button(frame_acao, text="Enviar Teste", command=envia_teste, state="disabled")
botao_acao.pack(fill="x", pady=5)


# 4. Resultados
frame_resultado = ttk.Labelframe(frame_esquerda, text="Status do Teste", padding="10")
frame_resultado.pack(fill="x", pady=5)

texto_resultado = ttk.Label(frame_resultado, text="Aguardando teste...", font=("Helvetica", 10, "italic"))
texto_resultado.pack(pady=5)

frame_direita = ttk.Frame(mainframe)
frame_direita.grid(row=0, column=1, sticky="nsew", padx=10)

frame_cadastro = ttk.Labelframe(frame_direita, text="Cadastrar Novo Componente", padding="15")
frame_cadastro.pack(fill="both", expand=True, pady=5)

# Campo Nome
ttk.Label(frame_cadastro, text="Nome do Componente:").pack(anchor="w", pady=(0,2))
entry_nome = ttk.Entry(frame_cadastro)
entry_nome.pack(fill="x", pady=(0,10))

# Campo Handshake
ttk.Label(frame_cadastro, text="Byte de Handshake (ex: 0x37):").pack(anchor="w", pady=(0,2))
entry_handshake = ttk.Entry(frame_cadastro)
entry_handshake.pack(fill="x", pady=(0,10))

# Campo Sucessos
ttk.Label(frame_cadastro, text="Bytes de Sucesso (separados por vírgula):").pack(anchor="w", pady=(0,2))
entry_sucessos = ttk.Entry(frame_cadastro)
entry_sucessos.pack(fill="x", pady=(0,2))
ttk.Label(frame_cadastro, text="Exemplo para RC522: 0x91,0x92", font=("Helvetica", 8, "italic"), foreground="gray").pack(anchor="w", pady=(0,15))

# Botão Salvar
botao_cadastrar = ttk.Button(frame_cadastro, text="Salvar no Banco (JSON)", command=cadastrar_novo_componente)
botao_cadastrar.pack(fill="x", ipady=5)


# Inicialização
inicializar_json()
carregar_componentes()
atualizar_portas()

# Fechamento seguro
raiz.protocol("WM_DELETE_WINDOW", ao_fechar)
raiz.mainloop()