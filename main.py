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
        # Inserir o RC522 como padrão inicial para facilitar (com 2 comandos de exemplo)
        dados_iniciais = [
            {"envio": "0x10", "sucessos": "0x91,0x92"},
            {"envio": "0x11", "sucessos": "0x95"}
        ]
        salvar_componente_json("Dummy", dados_iniciais)

def salvar_componente_json(nome, lista_comandos):
    """Carrega o JSON atual, adiciona/atualiza o componente com seus múltiplos pares e salva."""
    dados = {}
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, mode='r', encoding='utf-8') as f:
                dados = json.load(f)
        except json.JSONDecodeError:
            dados = {}
            
    # Guarda os comandos estruturados para o componente
    dados[nome] = {
        "Comandos": lista_comandos
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
                componentes_carregados[nome] = []
                for cmd in info.get("Comandos", []):
                    componentes_carregados[nome].append({
                        "handshake": cmd["envio"],
                        "sucessos": [s.strip() for s in cmd["sucessos"].split(",")]
                    })
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao ler o arquivo JSON: {e}")
            
    # Atualiza o combobox de seleção
    nomes = list(componentes_carregados.keys())
    combo_componentes['values'] = nomes
    if nomes:
        combo_componentes.current(0)

def cadastrar_novo_componente():
    nome = entry_nome.get().strip()
    linhas_texto = text_comandos.get("1.0", END).strip()
    
    if not nome or not linhas_texto:
        messagebox.showwarning("Aviso", "O nome e as configurações dos pares são obrigatórios!")
        return
        
    if nome in componentes_carregados:
        messagebox.showwarning("Aviso", "Já existe um componente com este nome!")
        return

    lista_comandos_validados = []
    
    # Processa cada linha digitada no Text box
    for linha in linhas_texto.split('\n'):
        linha = linha.strip()
        if not linha:
            continue
            
        if '=' not in linha:
            messagebox.showerror("Erro", f"Linha inválida: '{linha}'\nUse o formato: byte_envio = byte_sucesso1,byte_sucesso2")
            return
            
        handshake, sucessos = linha.split('=', 1)
        handshake = handshake.strip()
        sucessos = sucessos.strip()
        
        try:
            # Validação do formato do byte de envio
            int(handshake, 16) if '0x' in handshake else int(handshake)
            # Validação dos bytes de sucesso
            for s in sucessos.split(','):
                int(s.strip(), 16) if '0x' in s.strip() else int(s.strip())
        except ValueError:
            messagebox.showerror("Erro", f"Os endereços em '{linha}' devem ser inteiros ou hexadecimais (ex: 0x37)!")
            return
            
        lista_comandos_validados.append({
            "envio": handshake,
            "sucessos": sucessos
        })

    if not lista_comandos_validados:
        messagebox.showwarning("Aviso", "Insira pelo menos um par de envio/resposta!")
        return

    salvar_componente_json(nome, lista_comandos_validados)
    carregar_componentes() # Recarrega a lista
    
    # Limpa os campos de texto
    entry_nome.delete(0, END)
    text_comandos.delete("1.0", END)
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
        
    lista_pares = componentes_carregados[comp_selecionado]
    
    texto_resultado.config(text="Executando testes em sequência...")
    raiz.update_idletasks()
    
    status_final_msg = ""
    sucesso_geral = True

    # Executa o teste sequencial para CADA par cadastrado no componente
    for idx, par in enumerate(lista_pares, start=1):
        valor_digitado = par["handshake"]
        
        try:
            byte_com_conversao = int(valor_digitado, 16) if '0x' in valor_digitado else int(valor_digitado)
            
            # Limpa o buffer antes de enviar
            arduino.reset_input_buffer()
            arduino.write(bytes([byte_com_conversao]))
            
            time.sleep(0.1) # Pequena pausa para o Arduino processar e responder
            
            resposta_bruta = arduino.read(1)
            if resposta_bruta:
                valor_retornado = resposta_bruta[0]
                
                # Converte a lista de sucessos salvas em inteiros
                lista_sucessos_int = []
                for s in par["sucessos"]:
                    num = int(s, 16) if '0x' in s else int(s)
                    lista_sucessos_int.append(num)
                    
                if valor_retornado in [0x00, 0xFF]:
                    status_final_msg += f"Par #{idx} (Enviado {valor_digitado}): Erro físico (0x{valor_retornado:02X})\n"
                    sucesso_geral = False
                elif valor_retornado in lista_sucessos_int:
                    status_final_msg += f"Par #{idx} (Enviado {valor_digitado}): OK (0x{valor_retornado:02X})\n"
                else:
                    status_final_msg += f"Par #{idx} (Enviado {valor_digitado}): Inesperado (0x{valor_retornado:02X})\n"
                    sucesso_geral = False
            else:
                status_final_msg += f"Par #{idx} (Enviado {valor_digitado}): Timeout sem resposta\n"
                sucesso_geral = False
                
        except ValueError:
            status_final_msg += f"Par #{idx}: Erro ao processar dados hexadecimais.\n"
            sucesso_geral = False

    # Exibe o relatório consolidado na interface
    texto_resultado.config(text=status_final_msg.strip())
    
    if sucesso_geral:
        messagebox.showinfo("Resultado", f"Todos os testes do componente '{comp_selecionado}' passaram!")
    else:
        messagebox.showwarning("Resultado", f"Houve falhas nos testes do componente '{comp_selecionado}'.")
    
def ao_fechar():
    if arduino and arduino.is_open:
        arduino.close()
    raiz.destroy()

# --- INTERFACE GRÁFICA ---
raiz = Tk()
raiz.title("Gerenciador de Componentes & Arduino")
raiz.geometry("1200x600")

mainframe = ttk.Frame(raiz, padding="20")
mainframe.pack(fill=BOTH, expand=True)

mainframe.columnconfigure(0, weight=1) 
mainframe.columnconfigure(1, weight=1) 

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

texto_acao = ttk.Label(frame_acao, text="Testar todos os pares associados ao componente:")
texto_acao.pack(anchor="w")

botao_acao = ttk.Button(frame_acao, text="Enviar Teste Completo", command=envia_teste, state="disabled")
botao_acao.pack(fill="x", pady=5)


# 4. Resultados (Aumentado para acomodar várias linhas de resposta)
frame_resultado = ttk.Labelframe(frame_esquerda, text="Status do Teste", padding="10")
frame_resultado.pack(fill="both", expand=True, pady=5)

texto_resultado = ttk.Label(frame_resultado, text="Aguardando teste...", font=("Helvetica", 10, "italic"), justify=LEFT)
texto_resultado.pack(anchor="w", pady=5)

frame_direita = ttk.Frame(mainframe)
frame_direita.grid(row=0, column=1, sticky="nsew", padx=10)

frame_cadastro = ttk.Labelframe(frame_direita, text="Cadastrar Novo Componente", padding="15")
frame_cadastro.pack(fill="both", expand=True, pady=5)

# Campo Nome
ttk.Label(frame_cadastro, text="Nome do Componente:").pack(anchor="w", pady=(0,2))
entry_nome = ttk.Entry(frame_cadastro)
entry_nome.pack(fill="x", pady=(0,10))

# Campo de Texto para múltiplos Pares
ttk.Label(frame_cadastro, text="Pares Envio = Sucessos (um por linha):").pack(anchor="w", pady=(0,2))
text_comandos = Text(frame_cadastro, height=8, font=("Helvetica", 10))
text_comandos.pack(fill="x", pady=(0,2))

# Exemplo explicativo no cadastro
exemplo_txt = (
    "Exemplo:\n"
    "0x37 = 0x91,0x92\n"
    "0x38 = 0x95"
)
ttk.Label(frame_cadastro, text=exemplo_txt,justify=LEFT).pack(anchor="w", pady=(0,15))

# Botão Salvar
botao_cadastrar = ttk.Button(frame_cadastro, text="Salvar no Banco (JSON)", command=cadastrar_novo_componente)
botao_cadastrar.pack(fill="x", ipady=5)


# Inicialização
carregar_componentes()
atualizar_portas()

# Fechamento seguro
raiz.protocol("WM_DELETE_WINDOW", ao_fechar)
raiz.mainloop()