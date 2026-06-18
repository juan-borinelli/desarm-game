"""
=============================================================
  OPERAÇÃO DESATIVAÇÃO - Simulador de Desativação de Bomba
=============================================================
Temática: Um mapa de operação tática estilo Counter-Strike.
O jogador (CT) deve conter a expansão do vírus da bomba
enquanto gerencia recursos e toma decisões estratégicas.

Estados das células:
  . = Área Neutra (corredor/parede vazia)
  B = Bomba Ativa (zona de explosivo)
  T = Terrorista (agente inimigo)
  C = CT / Agente de Defesa
  E = Explosão / Área Contaminada
  S = Escudo / Barreira Defensiva
  D = Desativado (bomba neutralizada)

Regras de Evolução (simultâneas):
  1. B (Bomba) cercada por 3+ T vira E (explode / se expande)
  2. . (Neutra) com 2+ B vizinhas vira B (bomba se espalha)
  3. T com 0 vizinhos T ou B morre → vira . (isolado, recua)
  4. C com 3+ E vizinhas vira E (CT é eliminado pela explosão)
  5. S adjacente a B reduz: se tiver 2+ B vizinhas, S vira .
  6. E com 0 B vizinhas e 1+ C vizinhos vira D (área desativada)
  7. . com 2+ C vizinhos e 0 T vizinhos vira C (CT avança)
  8. T com 2+ T vizinhos avança: . vizinha com 3+ T vira T
  9. D permanece D (área já desativada é segura)
  10. C com 1+ S vizinho sobrevive: ignora regra 4

Condições de Vitória/Derrota:
  - Vitória: nenhuma célula B ou T no mapa após 10 rodadas
  - Derrota: mais de 60 células E no mapa (explosão catastrófica)
=============================================================
"""

import os
import time
import random

# ── Constantes ───────────────────────────────────────────────
ROWS, COLS = 15, 15
ESTADOS = {'.', 'B', 'T', 'C', 'E', 'S', 'D'}
MIN_RODADAS = 10

CREDITOS_INICIAIS = 500

ACOES = {
    '1': ('Posicionar CT (agente de defesa)',      80,  'C'),
    '2': ('Instalar Escudo defensivo',             120, 'S'),
    '3': ('Desativar Bomba manualmente',           200, 'D'),
    '4': ('Evacuar área (limpar célula)',          60,  '.'),
}

# ── Cores ANSI ───────────────────────────────────────────────
COR = {
    'B': '\033[91m',   # vermelho brilhante
    'T': '\033[31m',   # vermelho
    'C': '\033[94m',   # azul brilhante
    'E': '\033[93m',   # amarelo/laranja
    'S': '\033[96m',   # ciano
    'D': '\033[92m',   # verde
    '.': '\033[90m',   # cinza
    'RESET': '\033[0m',
    'TITULO': '\033[1;97m',
    'INFO':   '\033[1;33m',
    'ERRO':   '\033[1;31m',
    'OK':     '\033[1;32m',
}

def cor(estado):
    return COR.get(estado, '') + estado + COR['RESET']

# ── I/O de Arquivo ───────────────────────────────────────────
def ler_mundo(caminho='mundo.txt'):
    """Lê a matriz 15x15 do arquivo mundo.txt."""
    mundo = []
    with open(caminho, 'r') as f:
        for linha in f:
            celulas = linha.strip().split(' ')
            if len(celulas) != COLS:
                raise ValueError(f"Linha com {len(celulas)} colunas, esperado {COLS}.")
            for c in celulas:
                if c not in ESTADOS:
                    raise ValueError(f"Estado inválido: '{c}'")
            mundo.append(celulas)
    if len(mundo) != ROWS:
        raise ValueError(f"Matriz com {len(mundo)} linhas, esperado {ROWS}.")
    return mundo

def salvar_mundo(mundo, caminho='mundo_final.txt'):
    """Salva o estado final em mundo_final.txt."""
    with open(caminho, 'w') as f:
        for linha in mundo:
            f.write(' '.join(linha) + '\n')

def gerar_mundo_inicial():
    """Gera e salva um mundo.txt padrão se não existir."""
    # Layout tático: bases T (canto sup-esq), base CT (canto inf-dir)
    base = [
        ['T','T','T','.','.','.','.','.','.','.','.','.','.','.','C'],
        ['T','B','T','.','.','.','.','.','.','.','.','.','.','.','C'],
        ['T','T','.','.','.','.','.','.','.','.','.','.','.','.','C'],
        ['.','.','.','.','.','.','.','.','.','.','.','.','.','.','.'],
        ['.','.','.','.','.','B','.','.','.','.','.','.','.','.','S'],
        ['.','.','.','.','.','.','.','.','.','.','.','.','.','.','.'],
        ['.','.','.','.','.','.','B','.','.','.','.','.','.','.','S'],
        ['.','.','.','.','.','.','.','.','.','.','.','.','.','.','.'],
        ['S','.','.','.','.','.','.','.','.','.','.','.','.','.','.'],
        ['.','.','.','.','.','.','.','.','.','.','.','.','.','.','.'],
        ['S','.','.','.','.','.','.','.','.','.','T','T','.','.','.'],
        ['.','.','.','.','.','.','.','.','.','.','.','T','B','.','.'],
        ['C','.','.','.','.','.','.','.','.','.','.','.','.','.','T'],
        ['C','.','.','.','.','.','.','.','.','.','.','.','.','.','T'],
        ['C','C','.','.','.','.','.','.','.','.','.','.','.','T','T'],
    ]
    with open('mundo.txt', 'w') as f:
        for linha in base:
            f.write(' '.join(linha) + '\n')
    print(COR['OK'] + "[OK] mundo.txt gerado automaticamente." + COR['RESET'])

# ── Lógica do Jogo ───────────────────────────────────────────
def contar_vizinhos(mundo, r, c, estados_alvo):
    """Conta vizinhos de uma célula que estejam nos estados_alvo."""
    count = 0
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                if mundo[nr][nc] in estados_alvo:
                    count += 1
    return count

def evoluir(mundo):
    """
    Calcula a próxima geração do mapa aplicando todas as regras
    simultaneamente (usa o estado inicial para calcular cada célula).
    """
    novo = [linha[:] for linha in mundo]  # cópia profunda

    for r in range(ROWS):
        for c in range(COLS):
            celula = mundo[r][c]

            n_B = contar_vizinhos(mundo, r, c, {'B'})
            n_T = contar_vizinhos(mundo, r, c, {'T'})
            n_C = contar_vizinhos(mundo, r, c, {'C'})
            n_E = contar_vizinhos(mundo, r, c, {'E'})
            n_S = contar_vizinhos(mundo, r, c, {'S'})
            n_BT = contar_vizinhos(mundo, r, c, {'B', 'T'})

            # Regra 9: D permanece D
            if celula == 'D':
                novo[r][c] = 'D'

            # Regra 1: B com 3+ T vizinhos → E
            elif celula == 'B' and n_T >= 3:
                novo[r][c] = 'E'

            # Regra 2: . com 2+ B vizinhas → B
            elif celula == '.' and n_B >= 2:
                novo[r][c] = 'B'

            # Regra 3: T isolado (sem T ou B vizinhos) → .
            elif celula == 'T' and n_BT == 0:
                novo[r][c] = '.'

            # Regra 4 vs Regra 10: C com 3+ E vizinhas → E (salvo se tiver S vizinho)
            elif celula == 'C' and n_E >= 3:
                if n_S >= 1:
                    novo[r][c] = 'C'  # escudo protege
                else:
                    novo[r][c] = 'E'

            # Regra 5: S com 2+ B vizinhas → . (escudo destruído)
            elif celula == 'S' and n_B >= 2:
                novo[r][c] = '.'

            # Regra 6: E com 0 B vizinhas e 1+ C vizinhos → D
            elif celula == 'E' and n_B == 0 and n_C >= 1:
                novo[r][c] = 'D'

            # Regra 7: . com 2+ C e 0 T vizinhos → C (CT avança)
            elif celula == '.' and n_C >= 2 and n_T == 0:
                novo[r][c] = 'C'

            # Regra 8: . com 3+ T vizinhos → T (terroristas avançam)
            elif celula == '.' and n_T >= 3:
                novo[r][c] = 'T'

            # Caso contrário: mantém estado atual
            else:
                novo[r][c] = celula

    return novo

def contar_estados(mundo):
    """Retorna dicionário com contagem de cada estado no mapa."""
    contagem = {e: 0 for e in ESTADOS}
    for linha in mundo:
        for c in linha:
            contagem[c] += 1
    return contagem

# ── Interface ────────────────────────────────────────────────
def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def exibir_cabecalho(rodada, creditos):
    print(COR['TITULO'])
    print("╔══════════════════════════════════════════════════════╗")
    print("║         OPERAÇÃO DESATIVAÇÃO  ·  BOMB DEFUSAL        ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(COR['RESET'], end='')
    print(f"  {COR['INFO']}[ RODADA {rodada:02d}/{MIN_RODADAS} ]{COR['RESET']}   "
          f"Créditos: {COR['OK']}{creditos}$" + COR['RESET'])
    print()

def exibir_legenda():
    legenda = [
        ('B', 'Bomba Ativa'),
        ('T', 'Terrorista'),
        ('C', 'Agente CT'),
        ('E', 'Explosão'),
        ('S', 'Escudo'),
        ('D', 'Desativado'),
        ('.', 'Área Neutra'),
    ]
    print("  Legenda: ", end='')
    for estado, nome in legenda:
        print(f"{cor(estado)}={nome}  ", end='')
    print(COR['RESET'])
    print()

def exibir_mapa(mundo):
    # Cabeçalho de colunas
    print("     ", end='')
    for c in range(COLS):
        print(f"{c:2}", end='')
    print()
    print("    +" + "--" * COLS + "-+")
    for r in range(ROWS):
        print(f" {r:2} |", end='')
        for c in range(COLS):
            print(f" {cor(mundo[r][c])}", end='')
        print(" |")
    print("    +" + "--" * COLS + "-+")
    print()

def exibir_status(mundo):
    cont = contar_estados(mundo)
    print(f"  Status → "
          f"{cor('B')}:{cont['B']}  "
          f"{cor('T')}:{cont['T']}  "
          f"{cor('C')}:{cont['C']}  "
          f"{cor('E')}:{cont['E']}  "
          f"{cor('S')}:{cont['S']}  "
          f"{cor('D')}:{cont['D']}  "
          f"{cor('.')}:{cont['.']}  ")
    print()

def exibir_menu():
    print(COR['TITULO'] + "  ── MENU DE AÇÕES ─────────────────────────────────" + COR['RESET'])
    for chave, (nome, custo, _) in ACOES.items():
        print(f"  {chave}. {nome:<35} (Custo: {COR['INFO']}{custo}${COR['RESET']})")
    print(f"  5. Passar turno sem agir                          (Custo: 0$)")
    print()

def pedir_posicao(mundo, estado_proibido=None):
    """Solicita linha e coluna válidas ao usuário."""
    while True:
        try:
            entrada = input("  → Posição (linha coluna, ex: 7 3): ").strip()
            partes = entrada.split()
            r, c = int(partes[0]), int(partes[1])
            if not (0 <= r < ROWS and 0 <= c < COLS):
                print(COR['ERRO'] + "  Posição fora dos limites (0-14)." + COR['RESET'])
                continue
            if estado_proibido and mundo[r][c] == estado_proibido:
                print(COR['ERRO'] + f"  Célula já está no estado '{estado_proibido}'." + COR['RESET'])
                continue
            return r, c
        except (ValueError, IndexError):
            print(COR['ERRO'] + "  Entrada inválida. Digite dois números separados por espaço." + COR['RESET'])

def aplicar_acao(mundo, creditos):
    """Apresenta o menu e aplica a ação escolhida pelo usuário."""
    exibir_menu()
    escolha = input("  Escolha sua ação: ").strip()

    if escolha == '5':
        print(COR['OK'] + "  Turno passado sem ação." + COR['RESET'])
        time.sleep(1)
        return mundo, creditos

    if escolha not in ACOES:
        print(COR['ERRO'] + "  Opção inválida." + COR['RESET'])
        time.sleep(1)
        return mundo, creditos

    nome, custo, novo_estado = ACOES[escolha]

    if creditos < custo:
        print(COR['ERRO'] + f"  Créditos insuficientes! (Precisa de {custo}$, você tem {creditos}$)" + COR['RESET'])
        time.sleep(1.5)
        return mundo, creditos

    print(f"\n  Ação: {COR['INFO']}{nome}{COR['RESET']}")

    # Ação 3 (Desativar Bomba) só funciona em células B
    if escolha == '3':
        print("  Escolha a célula com BOMBA (B) para desativar:")
        r, c = pedir_posicao(mundo)
        if mundo[r][c] != 'B':
            print(COR['ERRO'] + "  Não há bomba nessa posição!" + COR['RESET'])
            time.sleep(1.5)
            return mundo, creditos
    else:
        print(f"  Escolha onde aplicar [{novo_estado}]:")
        r, c = pedir_posicao(mundo)

    mundo[r][c] = novo_estado
    creditos -= custo
    print(COR['OK'] + f"  ✔ Ação aplicada em ({r},{c})! Créditos restantes: {creditos}$" + COR['RESET'])
    time.sleep(1.2)
    return mundo, creditos

def verificar_vitoria_derrota(mundo, rodada):
    """
    Retorna:
      'vitoria' se não há B nem T no mapa
      'derrota'  se há mais de 60 células E
      None       caso contrário
    """
    cont = contar_estados(mundo)
    if cont['E'] > 60:
        return 'derrota'
    if cont['B'] == 0 and cont['T'] == 0:
        return 'vitoria'
    if rodada >= MIN_RODADAS and cont['B'] == 0 and cont['T'] == 0:
        return 'vitoria'
    return None

def tela_final(resultado, mundo, rodada):
    limpar_tela()
    cont = contar_estados(mundo)
    if resultado == 'vitoria':
        print(COR['OK'])
        print("╔══════════════════════════════════════════╗")
        print("║   ✔  OPERAÇÃO BEM-SUCEDIDA! VITÓRIA!     ║")
        print("╚══════════════════════════════════════════╝")
        print(COR['RESET'])
        print(f"  Todas as bombas foram desativadas em {rodada} rodadas!")
    else:
        print(COR['ERRO'])
        print("╔══════════════════════════════════════════╗")
        print("║   ✖  FALHA NA OPERAÇÃO - DERROTA!        ║")
        print("╚══════════════════════════════════════════╝")
        print(COR['RESET'])
        print(f"  A explosão tomou o mapa! {cont['E']} áreas destruídas.")
    print()
    print(f"  Resumo final: "
          f"Bombas={cont['B']}  Terroristas={cont['T']}  "
          f"CTs={cont['C']}  Explosões={cont['E']}  Desativados={cont['D']}")
    print()

# ── Loop Principal ───────────────────────────────────────────
def main():
    limpar_tela()

    # Carrega ou gera mundo inicial
    if not os.path.exists('mundo.txt'):
        print(COR['INFO'] + "Arquivo mundo.txt não encontrado. Gerando mapa padrão..." + COR['RESET'])
        gerar_mundo_inicial()
        time.sleep(1)

    try:
        mundo = ler_mundo('mundo.txt')
    except Exception as e:
        print(COR['ERRO'] + f"Erro ao ler mundo.txt: {e}" + COR['RESET'])
        return

    creditos = CREDITOS_INICIAIS
    rodada = 1
    resultado = None

    while True:
        limpar_tela()
        exibir_cabecalho(rodada, creditos)
        exibir_legenda()
        exibir_mapa(mundo)
        exibir_status(mundo)

        # Verifica condições a cada rodada
        resultado = verificar_vitoria_derrota(mundo, rodada)
        if resultado:
            break

        # Ação do usuário
        mundo, creditos = aplicar_acao(mundo, creditos)

        # Evolução simultânea
        mundo = evoluir(mundo)

        # Ganho de créditos por rodada
        cont = contar_estados(mundo)
        ganho = max(0, cont['D'] * 10 + cont['C'] * 5 - cont['E'] * 3)
        creditos += ganho
        if ganho > 0:
            print(COR['OK'] + f"  + {ganho}$ ganhos por progresso tático." + COR['RESET'])
            time.sleep(0.8)

        # Após MIN_RODADAS, verifica derrota/vitória definitiva
        if rodada >= MIN_RODADAS:
            resultado = verificar_vitoria_derrota(mundo, rodada)
            if resultado is None:
                # Continua até resolver ou catástrofe
                resultado = verificar_vitoria_derrota(mundo, rodada)
                if resultado is None:
                    print(COR['INFO'] + f"\n  Rodada mínima atingida. Jogo continua até resolução..." + COR['RESET'])
                    time.sleep(1)

        rodada += 1

    # Exibe tela final
    tela_final(resultado, mundo, rodada - 1)
    exibir_mapa(mundo)
    salvar_mundo(mundo)
    print(COR['OK'] + "  Estado final salvo em 'mundo_final.txt'." + COR['RESET'])
    print()

if __name__ == '__main__':
    main()
