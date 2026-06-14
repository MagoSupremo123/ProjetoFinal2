from tkinter import *
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import time

arduino = None

def atualizar_portas():
  portas = serial.tools.list_ports.comports()
  lista_portas = [porta.device for porta in portas]
    
  combo_portas['values'] = lista_portas
  if lista_portas:
    combo_portas.current(0) # Seleciona a primeira porta encontrada
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

  # Se já houver uma conexão aberta, fecha antes de abrir outra
  if arduino and arduino.is_open:
    arduino.close()

  try:
    arduino = serial.Serial(porta_selecionada, 9600, timeout=1)
    texto_status.config(text=f"Conectado em {porta_selecionada}")
    time.sleep(2) # Espera o Arduino resetar
    botao_acao.config(state="normal") # Ativa o botão do LED
  except Exception as e:
    texto_status.config(text="Erro ao conectar!")
    messagebox.showerror("Erro", f"Não foi possível conectar à porta {porta_selecionada}.\n{e}")
    botao_acao.config(state="disabled")

def envia_teste():
  if not arduino or not arduino.is_open:
    messagebox.showerror("Erro", "O arduino não está conectado")
    return
  
  valor_digitado = byte_leitura.get()
  if valor_digitado:
    try:
      byte_com_conversao = int(valor_digitado, 16) if '0x' in valor_digitado else int(valor_digitado)
      arduino.write(bytes([byte_com_conversao]))
    
      texto_resultado.config(text="Aguardando resposta...")
      raiz.update_idletasks() # Força a interface a atualizar o texto antes de travar na leitura

      # Aguarda e lê 1 byte de resposta enviado pelo Arduino
      resposta_bruta = arduino.read(1)
      if resposta_bruta:
        # Transforma o byte recebido em um número inteiro para exibição
        valor_retornado = resposta_bruta[0]
        status_msg = f"Resposta: 0x{valor_retornado:02X} - "
                
        # Validação do Handshake
        if valor_retornado in [0x00, 0xFF]:
          status_msg += "Erro físico RC522."
        elif valor_retornado in [0x91, 0x92]:
          status_msg += "Sucesso! RC522 OK."
        else:
          status_msg += "Resposta desconhecida."
             
        # Atualiza a label de status na interface gráfica
        texto_status.config(text=status_msg)
                
      else:
        texto_resultado.config(text="Erro: Sem resposta (Timeout).")
        messagebox.showerror("Timeout", "O Arduino não respondeu dentro do tempo limite.")
    
    except ValueError:
      messagebox.showerror("Erro", "Digite um valor hexadecimal ou inteiro válido!")
    
def ao_fechar():
  if arduino and arduino.is_open:
    arduino.close()
  raiz.destroy()

raiz = Tk()
raiz.title("Meu Aplicativo")
raiz.geometry("800x600")

mainframe = ttk.Frame(raiz)
mainframe.pack(expand=True)

# Seleciona porta
frame_conexao = ttk.Labelframe(mainframe, text="Conexão")

texto_conexao = ttk.Label(frame_conexao, text="Selecionar porta:")
texto_conexao.pack()

combo_portas = ttk.Combobox(frame_conexao, state="readonly")
combo_portas.pack()

botao_atualizar = ttk.Button(frame_conexao, text="Atualizar", command=atualizar_portas)
botao_atualizar.pack()

botao_conectar = ttk.Button(frame_conexao, text="Conectar", command=conectar_arduino)
botao_conectar.pack()

texto_status = ttk.Label(frame_conexao, text="Não conectado")
texto_status.pack()

frame_conexao.pack()

# Configura o teste
frame_config = ttk.Labelframe(mainframe, text="Configuração")

texto_config = ttk.Label(frame_config, text="Byte de leitura:")
texto_config.pack()

byte_leitura = StringVar()
entrada = ttk.Entry(frame_config, textvariable=byte_leitura) # Por exemplo 0x37
entrada.pack()

frame_config.pack()

# Executa o teste
frame_acao = ttk.Labelframe(mainframe, text="Ação")

texto_acao = ttk.Label(frame_acao, text="Enviar endereço de leitura para o arduino:")
texto_acao.pack()

botao_acao = ttk.Button(frame_acao, text="Enviar", command=envia_teste, state="disabled")
botao_acao.pack()

frame_acao.pack()

# Mostra o resultado
frame_resultado = ttk.Labelframe(mainframe, text="Ação")

texto_resultado = ttk.Label(frame_resultado, text="Aguardando teste...")
texto_resultado.pack()

frame_resultado.pack()

# Executa a busca de portas logo ao iniciar o programa
atualizar_portas()

# Fechamento
raiz.protocol("WM_DELETE_WINDOW", ao_fechar)

raiz.mainloop()
