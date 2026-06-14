#include <SPI.h>

// Definições de pinos para o Arduino Mega
const int SS_PIN = 53;   // Slave Select (SDA)
const int RST_PIN = 5;   // Reset

void setup() {
  // Inicia a comunicação Serial na velocidade de 9600 bps (mesma que usaremos no Python)
  Serial.begin(9600);
  
  // Configura os pinos de controle do RC522 como saídas
  pinMode(SS_PIN, OUTPUT);
  pinMode(RST_PIN, OUTPUT);
  
  // Garante que o Slave Select comece em HIGH (comunicação desativada)
  digitalWrite(SS_PIN, HIGH);

  // Inicializa/Acorda o RC522 dando um pulso no pino Reset
  digitalWrite(RST_PIN, LOW);
  delay(10);
  digitalWrite(RST_PIN, HIGH);
  delay(50); // Aguarda o chip estabilizar internamente

  // Inicia o barramento SPI do Arduino Mega (Pinos 50, 51, 52)
  SPI.begin();
}

void loop() {
  // Verifica se o Python enviou algum byte pela Serial
  if (Serial.available() > 0) {
    
    // Lê o byte enviado pelo Python (Ex: se o Python mandar 0x37, a variável terá 0x37)
    byte registradorAlvo = Serial.read(); 
    
    // Converte o endereço puro para o formato de LEITURA exigido pelo RC522:
    // 1. Desloca os bits 1 posição para a esquerda (<< 1)
    // 2. Define o bit mais significativo (MSB) como 1 usando uma máscara OU (| 0x80)
    // Se registradorAlvo for 0x37, comandoSPI se tornará 0xEE
    byte comandoSPI = (registradorAlvo << 1) | 0x80; 

    // --- Comunicação SPI com o RC522 ---
    
    // 1. Ativa o chip RC522 colocando o pino SS em LOW
    digitalWrite(SS_PIN, LOW);

    // 2. Envia o comando de leitura que calculamos (0xEE)
    SPI.transfer(comandoSPI);

    // 3. Envia um byte "dummy" (0x00) apenas para gerar o sinal de clock e receber o dado do chip
    byte valorRegistrador = SPI.transfer(0x00);

    // 4. Desativa o chip RC522 colocando o pino SS de volta em HIGH
    digitalWrite(SS_PIN, HIGH);
    
    // --- Fim da comunicação SPI ---

    // Envia o byte de resposta bruto (em formato binário) de volta para o Python
    Serial.write(valorRegistrador); 
  }
}