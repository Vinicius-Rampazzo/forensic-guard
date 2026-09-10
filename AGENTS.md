# Guia para agentes de IA — ForensicGuard

Leia este arquivo antes de escrever qualquer código neste repositório.

O estado atual do projeto e a próxima etapa estão em
[`docs/roadmap.md`](docs/roadmap.md). A especificação técnica original está em
[`docs/project-context.md`](docs/project-context.md) — leia a seção
"Divergências conhecidas" do roadmap antes de segui-la ao pé da letra.

---

## O projeto

Ferramenta open source de triagem forense. Recebe um arquivo, uma imagem ou um
e-mail `.eml`, executa análise **estática**, e devolve hashes, metadados,
indicadores explicáveis e um Risk Score.

Sem banco de dados. Sem autenticação. Sem persistência. Local-first.

O sistema **nunca afirma que algo é malware**. Ele apresenta indicadores e uma
pontuação heurística, sempre com a evidência que a justificou.

---

## Regras de colaboração

O dono do projeto é o Vinicius. Ele é o engenheiro que decide; o agente executa
e explica.

1. **Nunca rode comandos git.** Nada de `add`, `commit`, `branch`, `checkout`,
   `merge`, `push`. Apenas leitura (`status`, `diff`, `log`). Entregue o comando
   pronto para ele executar.
2. **Nunca crie branches de antemão.** Trabalhe na branch atual. Quando a etapa
   fecha, ele commita e só então decide qual é a próxima e como se chama.
3. **Toda bifurcação vira pergunta**, com as opções e o trade-off explícitos.
   Não escolha sozinho quando houver mais de um caminho razoável.
4. **Explique antes e depois** de cada bloco de trabalho: o que vai fazer e por
   quê; depois, o que mudou e como validar.
5. **Ensinar faz parte do trabalho.** Ele quer entender os conceitos e a lógica
   por trás de cada decisão, não receber código pronto.
6. **Ao fim de cada etapa**, entregue: resumo, checklist de validação manual,
   sugestão de mensagem de commit, e uma *proposta* do próximo recorte.

---

## Convenções de código

| Em inglês | Em português |
| --- | --- |
| Identificadores (variáveis, funções, classes, arquivos) | Comentários |
| Strings de UI e mensagens da API | Docstrings |
| IDs de indicadores | Mensagens de commit (descrição) |
| README e saída de programa (`dev.py --help`) | Conversa com o usuário |

**Commits** seguem Conventional Commits com **prefixo em inglês** e
**descrição em português**:

```
feat: adiciona detecção de tipo por magic bytes
fix: corrige leitura de arquivos maiores que o bloco
docs: atualiza instruções de instalação no Linux
test: organiza testes em classes
chore: atualiza dependências do backend
refactor: extrai leitura em blocos para módulo próprio
```

---

## Arquitetura

Backend e frontend são projetos separados que só se falam por HTTP.

O backend é organizado em camadas, e **a dependência sempre aponta para
baixo**:

```
api/routes/     fala HTTP. Recebe requisição, devolve resposta.
     ↓          Não sabe calcular hash.
services/       orquestra. Decide qual analisador chamar e em que ordem.
     ↓          Não sabe o que é uma requisição HTTP.
analyzers/      analisa um tipo de evidência.
     ↓
utils/          funções puras: hash, entropia, leitura, assinaturas.
                Não sabem nada do resto do sistema.
```

Teste para saber se a camada foi respeitada: **um módulo de `utils/` deve
funcionar copiado para qualquer outro projeto Python, sem alterações.** Se
precisar importar algo de `api/` ou `services/`, a camada está furada.

Valores de configuração vivem em `constants/` ou no `Settings`
(`app/config.py`), nunca espalhados pelo código como números mágicos.

---

## Regras de segurança

A aplicação processa arquivos **hostis por definição**. Assuma que todo upload
é malicioso.

- Nunca executar, importar ou interpretar o conteúdo analisado.
- Nunca confiar no nome de arquivo enviado — gerar identificador interno (UUID).
- Todo laço que cresce com a entrada precisa de teto (tamanho, quantidade,
  profundidade de recursão).
- Ler arquivos **sempre em blocos**, via `app/utils/streaming.py`. Nunca
  `path.read_bytes()` em evidência.
- Arquivos temporários são removidos em `finally`, mesmo quando há exceção.
- Parsers de formato hostil sempre dentro de `try/except`.
- Quando um limite corta a análise, o resultado precisa **informar** que é
  parcial. Relatório forense não pode dar a entender que examinou tudo.

---

## Dependências

**Higiene:** uma biblioteca só entra no `requirements.txt` na etapa em que
passa a ser usada de fato. Nada de instalar antecipadamente.

Versões sempre fixadas com `==`, para builds reprodutíveis.

`requirements.txt` = execução. `requirements-dev.txt` = desenvolvimento
(importa o primeiro com `-r`).

Quando uma dependência muda, ou quando o processo de instalação muda,
**o README precisa ser atualizado na mesma leva**, com instruções para
**Windows e Linux**.

---

## Testes

Rodar com `python backend/dev.py test`.

- Organizados em **classes por assunto**, com docstring explicando o que cada
  teste verifica.
- Fixtures **geradas por código**, byte a byte. Nenhum binário entra no
  repositório — ninguém deve baixar arquivo suspeito ao clonar uma ferramenta
  forense.
- Testar contra **verdade externa**, não contra a própria implementação. Os
  hashes são conferidos com vetores publicados do NIST; a entropia, com
  extremos matemáticos conhecidos.
- Limitação conhecida vira **teste explícito documentando o comportamento
  real**, nunca teste ajustado para passar escondendo o problema.

---

## Comandos

```bash
python backend/dev.py           # sobe a API em http://127.0.0.1:8000
python backend/dev.py test      # testes
python backend/dev.py lint      # ruff
python backend/dev.py format    # formata com ruff
python backend/dev.py check     # lint + testes, antes de commitar
python backend/dev.py --help

npm --prefix frontend run dev    # interface em http://localhost:3000
npm --prefix frontend run build  # build de produção, checa TypeScript
npm --prefix frontend run lint
```

O `dev.py` cria o ambiente virtual e instala dependências sozinho. Não é
necessário ativar o venv.

---

## Decisões já tomadas — não reabrir sem falar com o Vinicius

| Decisão | Motivo |
| --- | --- |
| **`python-magic` está fora** | Exige libmagic/DLL e quebra no Windows. Usamos tabela própria de magic bytes em `constants/signatures.py` mais `puremagic` como segunda opinião. |
| **`dev.py` como executor de tarefas** | Python não tem equivalente ao `npm run`. Script próprio, sem dependência externa, com bootstrap automático do venv. |
| **`httpx2` em vez de `httpx`** | Starlette 1.6 deprecou o `httpx` no `TestClient`. |
| **Leitura sempre em blocos** | `path.read_bytes()` em upload de 500 MB é vetor de negação de serviço. |
| **Hashes e entropia em funções independentes** | Cada uma faz sua leitura. O cache do sistema operacional torna o custo baixo, e a testabilidade compensa. |
| **Sem arquivos placeholder vazios** | Cada arquivo nasce com conteúdo. As pastas existem via `__init__.py`. |

---

## Fora do escopo — não implementar sem pedido explícito

Banco de dados, autenticação, histórico, painel administrativo, IA/LLM,
VirusTotal obrigatório, sandbox, análise dinâmica, execução de macros, YARA,
Volatility, PCAP, Docker, CLI, filas, Redis, microserviços.

Todos estão listados como "futuro" na especificação — e continuam lá.
