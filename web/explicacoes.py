"""Conteudo educativo das telas (portugues, com LaTeX inline $...$)."""

EXPLICACOES = {
    "inicio": {
        "titulo": "Bem-vindo ao Matrix Optimization",
        "resumo": (
            "Este aplicativo oferece ferramentas de **algebra linear** e **otimizacao** com "
            "explicacoes passo a passo. Escolha um modulo no menu lateral.\n\n"
            "Cada modulo resolve o problema digitado, mostra o resultado, os passos do calculo "
            "e um grafico quando possivel. Matrizes aceitam **fracoes** (ex: `1/3`)."
        ),
    },
    "gauss": {
        "titulo": "Resolucao de Sistemas Lineares (Gauss-Jordan)",
        "resumo": (
            "O metodo de **eliminacao de Gauss-Jordan** resolve sistemas de equacoes lineares "
            "da forma $Ax = b$, onde $A$ e a matriz de coeficientes, $x$ o vetor de incognitas "
            "e $b$ o vetor de termos independentes.\n\n"
            "O algoritmo opera sobre a **matriz aumentada** $[A \\mid b]$ aplicando operacoes "
            "elementares de linha (trocar linhas, multiplicar por constante, somar multiplo de "
            "outra linha) ate obter a forma **escalonada reduzida (RREF)**: pivos iguais a 1 e "
            "zerados acima e abaixo, quando possivel.\n\n"
            "Ao final, o sistema pode ter:\n"
            "- **Solucao unica**: todos os pivos presentes; cada variavel vale o termo independente.\n"
            "- **Infinitas solucoes**: ha variaveis livres (colunas sem pivo).\n"
            "- **Nenhuma solucao (inconsistente)**: uma linha $0 = \\text{constante} \\neq 0$."
        ),
        "formula": "Ax = b, \\qquad [A \\mid b] \\xrightarrow{\\text{RREF}} [I \\mid x]",
        "variaveis": [
            ("m", "Numero de equacoes (linhas da matriz)."),
            ("n", "Numero de variaveis (colunas de coeficientes). A matriz aumentada tera n + 1 colunas."),
            ("Matriz aumentada", "Cada linha representa uma equacao: os n coeficientes das variaveis "
             "seguidos do termo independente. Ex.: `2 1 8` representa $2x_1 + x_2 = 8$."),
        ],
    },
    "simplex": {
        "titulo": "Otimizacao Linear (Metodo Simplex)",
        "resumo": (
            "O **metodo Simplex** resolve problemas de programacao linear: maximizar a funcao "
            "objetivo $z = c^T x$ sujeita a restricoes lineares $Ax \\leq b$ e $x \\geq 0$.\n\n"
            "Para transformar as desigualdades em igualdades, cada restricao ganha uma **variavel "
            "de folga** $s_i \\geq 0$, formando o *tableau*. O algoritmo caminha de vertice em "
            "vertice da regiao viavel, sempre aumentando o valor de $z$, ate nao existir mais "
            "coeficiente negativo na linha da funcao objetivo (criterio de otimalidade)."
        ),
        "formula": "\\max z = \\sum_{j=1}^{n} c_j x_j, \\qquad \\sum_{j=1}^{n} A_{ij} x_j \\leq b_i, \\qquad x_j \\geq 0",
        "variaveis": [
            ("n", "Numero de variaveis de decisao (x_1, ..., x_n)."),
            ("m", "Numero de restricoes (limitacoes de recursos)."),
            ("c", "Coeficientes da funcao objetivo: lucro (ou custo) por unidade de cada variavel."),
            ("A", "Coeficientes das restricoes: $A_{ij}$ = quantidade do recurso i consumida por "
             "unidade produzida da variavel j. Cada linha e uma restricao."),
            ("b", "Limites (disponibilidade/capacidade) de cada recurso i."),
        ],
        "extra": "No grafico (para 2 variaveis) a regiao viavel e o poligono limitado pelas "
                 "restricoes; as linhas tracejadas sao niveis de $z$ e a estrela o ponto otimo.",
    },
    "newton": {
        "titulo": "Equacoes Nao Lineares (Newton-Raphson)",
        "resumo": (
            "O metodo de **Newton-Raphson** encontra solucoes (raizes) de sistemas de equacoes "
            "nao lineares $F(x) = 0$, onde $F: \\mathbb{R}^n \\to \\mathbb{R}^n$.\n\n"
            "Partindo de um **chute inicial** $x_0$ proximo da raiz, o algoritmo usa o "
            "**Jacobiano** $J(x)$ (matriz das derivadas parciais) para linearizar o sistema e "
            "calcular o proximo passo, repetindo ate que $\\|F(x)\\| \\leq \\text{tol}$.\n\n"
            "Funcoes suportadas: `+ - * / ** sin cos tan exp log log10 sqrt abs pi e` e "
            "variaveis `x1, x2, ...`."
        ),
        "formula": "x_{k+1} = x_k - J^{-1}(x_k)\\,F(x_k)",
        "variaveis": [
            ("n", "Numero de incognitas (e de equacoes)."),
            ("F_i", "Cada expressao deve ser digitada como $F_i(x)=0$, sem o sinal de igual. "
             "Ex.: `x1 + x2 - 3`.\n"),
            ("x0", "Chute inicial: ponto central da linearizacao. Quanto mais proximo da raiz, "
             "mais rapida a convergencia."),
            ("Tolerancia", "Residuo maximo $\\|F(x)\\|$ aceito para declarar convergencia "
             "(padrao 1e-12)."),
            ("Max int iteracoes", "Limite de seguranca para evitar iteracoes infinitas."),
            ("Line search", "Newton amortecido: reduz o passo quando o residuo nao diminui, "
             "melhorando a convergencia global."),
        ],
    },
    "otimizacao": {
        "titulo": "Otimizacao Nao Linear (SciPy)",
        "resumo": (
            "Otimiza funcoes objetivo **nao lineares** $f(x)$ com ou sem restricoes, usando o "
            "mecanismo da SciPy (metodo SLSQP quando ha restricoes ou limites).\n\n"
            "Sao suportadas restricoes de igualdade $g(x) = 0$, desigualdade $h(x) \\geq 0$ e "
            "limites $l_j \\leq x_j \\leq u_j$ por variavel. Gradientes e Hessianas sao "
            "calculados por diferenciacao **complex-step**, de precisao de maquina."
        ),
        "formula": "\\max_{x} f(x) \\quad \\text{sujeito a} \\quad g(x) = 0,\\; h(x) \\geq 0,\\; l \\leq x \\leq u",
        "variaveis": [
            ("n", "Numero de variaveis de decisao."),
            ("Funcao objetivo", "Expressao customizada usando `x1, x2, ...`. Ex.: "
             "`-x1**2 - x2**2 + 4*x1 + 6*x2`."),
            ("Max / Min", "Tipo de otimizacao: maximizar ou minimizar a funcao."),
            ("Igualdades", "Restricoes $g(x) = 0$, digitadas como expressao que deve zerar. "
             "Ex.: `x1 + 2*x2 - 10`."),
            ("Desigualdades", "Restricoes $h(x) \\geq 0$, na mesma forma. Ex.: `8 - x1**2 - x2**2` "
             "equivale a $x_1^2 + x_2^2 \\leq 8$."),
            ("Limites", "Intervalo de cada variavel; deixe em branco para sem limite."),
            ("x0", "Chute inicial (importante em problemas nao convexos)."),
        ],
    },
    "investimento": {
        "titulo": "Otimizacao de Portfolio de Investimentos",
        "resumo": (
            "Distribui um **orcamento** $B$ entre $n$ investimentos para maximizar o retorno "
            "total $R(x) = \\sum_i f_i(x_i)$, respeitando a restricao $\\sum_i x_i = B$ e "
            "limites individuais $0 \\leq l_i \\leq x_i \\leq u_i$.\n\n"
            "No otimo (uma alocacao interior), o principio de **retornos marginais iguais** vale: "
            "se aumentar R$1 em um investimento rendesse mais que em outro, seria melhor "
            "realocar o dinheiro. A condicao de **Karush-Kuhn-Tucker (KKT)** formaliza isso: "
            "$f_i'(x_i) = \\lambda$ para todos os investimentos ativos."
        ),
        "formula": "\\max R(x) = \\sum_{i=1}^{n} f_i(x_i) \\quad \\text{sujeito a} \\quad \\sum_{i=1}^{n} x_i = B,\\; x_i \\geq 0",
        "variaveis": [
            ("Orcamento B", "Capital total a ser distribuido entre os investimentos."),
            ("f_i(x)", "Funcao de retorno de cada investimento. Tipos:"),
            ("Logaritmica [L]", "$a \\ln(x + c)$ — utilidade concava com retorno decrescente. "
             "$a$: escala do retorno; $c$: deslocamento ($x + c > 0$)."),
            ("Exponencial [E]", "$a(1 - e^{-bx})$ — retorno saturante (aproxima $a$). "
             "$a$: retorno assintotico maximo; $b$: velocidade de saturacao."),
            ("Potencia [P]", "$a\\,x^{p}$ — concava para $0 < p \\leq 1$. $a$: escala; "
             "$p$: grau de concavidade."),
            ("Quadratica [Q]", "$a x - b x^2$ — concava, com retorno marginal linear "
             "decrescente. $a$: inclinacao inicial; $b$: decaimento."),
            ("Limites superiores", "Capacidade max de cada investimento (opcional)."),
        ],
    },
}


def obter(tela: str) -> dict:
    return EXPLICACOES[tela]