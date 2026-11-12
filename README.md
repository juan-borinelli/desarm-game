# 💣 Operação Desativação — Bomb Defusal

Simulador de desativação de bomba para terminal, escrito em Python. O mapa é um tabuleiro 15×15 que evolui sozinho a cada rodada, no estilo de um autômato celular (como o Jogo da Vida de Conway), com temática tática inspirada em Counter-Strike.

Você joga como o lado **CT**: a cada turno escolhe uma ação, gasta créditos e tenta conter o avanço das bombas e dos terroristas antes que a explosão tome o mapa.

## Integrantes

- Juan
- Matheus
- Bernardo Poluceno
- Gabriel

## Requisitos

- Python 3.6 ou superior
- Nenhuma biblioteca externa (só `os`, `time` e `random`, da biblioteca padrão)
- Um terminal com suporte a cores ANSI (Linux, macOS, Windows Terminal ou o PowerShell mais recente)

## Como executar

```bash
git clone https://github.com/juan-borinelli/desarm-game.git
cd desarm-game
python3 jogo.py
```

> No Windows, use `python jogo.py`.

Se o arquivo `mundo.txt` não existir, o jogo gera um mapa padrão automaticamente. Ao final da partida, o estado do tabuleiro é salvo em `mundo_final.txt`.

## O mapa

Cada célula do tabuleiro está em um destes estados:

| Símbolo | Estado | Descrição |
|:---:|---|---|
| `.` | Área Neutra | Corredor ou espaço vazio |
| `B` | Bomba Ativa | Zona com explosivo, se espalha pelo mapa |
| `T` | Terrorista | Agente inimigo |
| `C` | CT | Agente de defesa (o seu lado) |
| `E` | Explosão | Área contaminada |
| `S` | Escudo | Barreira defensiva |
| `D` | Desativado | Bomba neutralizada, área segura |

### Mapa personalizado

Você pode editar o `mundo.txt` para criar seu próprio cenário. O arquivo precisa ter **15 linhas com 15 símbolos cada**, separados por um espaço, usando só os símbolos da tabela acima. Exemplo de uma linha:

```
T T T . . . . . . . . . . . C
```

Se o formato estiver errado, o jogo mostra o erro e não inicia.

## Como jogar

Cada rodada segue esta ordem:

1. O mapa e o placar de cada estado são exibidos.
2. Você escolhe **uma ação** do menu e a posição (`linha coluna`, de 0 a 14).
3. O mapa evolui de acordo com as regras.
4. Você recebe créditos pelo progresso.

### Ações

Você começa com **500$** de crédito.

| Opção | Ação | Custo | Efeito |
|:---:|---|:---:|---|
| 1 | Posicionar CT | 80$ | Coloca um `C` na célula escolhida |
| 2 | Instalar Escudo | 120$ | Coloca um `S` na célula escolhida |
| 3 | Desativar Bomba | 200$ | Transforma um `B` em `D` (só funciona em células com bomba) |
| 4 | Evacuar área | 60$ | Limpa a célula, transformando em `.` |
| 5 | Passar o turno | 0$ | Não faz nada |

### Ganho de créditos

Depois de cada evolução você recebe:

```
ganho = 10 × (células D) + 5 × (células C) − 3 × (células E)
```

O ganho nunca é negativo: se o resultado der menos que zero, você simplesmente não ganha nada naquela rodada.

## Regras de evolução

Todas as regras são aplicadas **ao mesmo tempo**: o próximo estado de cada célula é calculado a partir do mapa da rodada anterior. A vizinhança considera as 8 células ao redor (incluindo diagonais).

| # | Célula | Condição | Vira |
|:---:|:---:|---|:---:|
| 1 | `B` | 3 ou mais `T` vizinhos | `E` (explode) |
| 2 | `.` | 2 ou mais `B` vizinhas | `B` (bomba se espalha) |
| 3 | `T` | Nenhum `T` ou `B` vizinho | `.` (isolado, recua) |
| 4 | `C` | 3 ou mais `E` vizinhas | `E` (CT eliminado) |
| 5 | `S` | 2 ou mais `B` vizinhas | `.` (escudo destruído) |
| 6 | `E` | Nenhuma `B` vizinha e pelo menos 1 `C` vizinho | `D` (área desativada) |
| 7 | `.` | 2 ou mais `C` vizinhos e nenhum `T` vizinho | `C` (CT avança) |
| 8 | `.` | 3 ou mais `T` vizinhos | `T` (terroristas avançam) |
| 9 | `D` | Sempre | `D` (área segura é permanente) |
| 10 | `C` | Pelo menos 1 `S` vizinho | Ignora a regra 4 (o escudo protege) |

Para células neutras (`.`), as regras são verificadas nesta ordem de prioridade: o espalhamento da bomba (regra 2) vem antes do avanço do CT (regra 7), que vem antes do avanço dos terroristas (regra 8).

## Vitória e derrota

- ✅ **Vitória:** não sobra nenhuma bomba (`B`) nem terrorista (`T`) no mapa.
- ❌ **Derrota:** o mapa passa de **60 células de explosão** (`E`).

O jogo tem uma referência de 10 rodadas, mas não para aí: depois da 10ª rodada a partida continua até que uma das condições acima aconteça.

## Dicas

- Escudos ao lado dos seus CTs os protegem das explosões.
- CTs perto de áreas de explosão sem bombas ao redor transformam essas áreas em zonas desativadas, que rendem 10$ por rodada cada.
- Terroristas isolados recuam sozinhos. Às vezes vale mais cortar o grupo deles do que atacar de frente.
- Duas bombas próximas se espalham rápido pelas áreas neutras entre elas. Desative uma antes que se multipliquem.

## Estrutura do projeto

```
desarm-game/
├── jogo.py       # código do jogo (lógica, regras, interface e loop principal)
├── mundo.txt     # mapa inicial 15×15
└── README.md
```
