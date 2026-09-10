# Roadmap do ForensicGuard

Fonte única da verdade sobre **onde o projeto está** e **o que vem a seguir**.
Atualizar ao fim de cada etapa.

O plano é uma ordem sugerida, não um compromisso. Etapas podem ser
reordenadas, divididas ou cortadas — a decisão é sempre do Vinicius.

**Convenção de trabalho:** uma etapa por sessão, uma branch por etapa. Nenhuma
branch é criada de antemão: quando a etapa fecha, ele commita, integra na
`main` e só então decide qual é a próxima.

---

## Estado atual

| | |
| --- | --- |
| **Última etapa concluída** | Etapa 2 — Núcleo de análise de arquivo |
| **Próxima etapa** | Etapa 3 — Detecção de tipo |
| **Nada funciona ponta a ponta ainda** | A primeira entrega visível é a Etapa 4, quando o `POST /analyze` conecta as peças |

---

## Etapa 1 — Estrutura ✅

Branch: `main` · Commit: `8e210e6`

- [x] `.gitignore`, README e especificação técnica versionada
- [x] Backend: FastAPI com *application factory* e CORS
- [x] Backend: configuração via `pydantic-settings` e `.env`
- [x] Backend: `GET /health` com schema Pydantic
- [x] Backend: pytest e ruff configurados
- [x] Backend: `dev.py` — executor de tarefas com bootstrap automático do venv
- [x] Frontend: Next.js 16 + TypeScript + Tailwind 4
- [x] Frontend: camada `services/api.ts` e `types/api.ts`
- [x] Frontend: landing com badge de status da API
- [x] README com instalação para Windows e Linux

---

## Etapa 2 — Núcleo de análise de arquivo ✅

Branch: `feat/file-core` · Commit: `0d02a26`

- [x] `utils/streaming.py` — leitura em blocos *(não previsto; extraído quando um teste expôs acoplamento entre entropia e hashing)*
- [x] `utils/hashing.py` — MD5, SHA-1, SHA-256, SHA-512 num único passe
- [x] `utils/entropy.py` — entropia de Shannon
- [x] `analyzers/string_analyzer.py` — strings ASCII e UTF-16LE
- [x] Regex: URL, IPv4, IPv6, e-mail, caminhos Windows, LOLBins/PowerShell
- [x] 45 testes, organizados em classes, com fixtures geradas por código

---

## Etapa 3 — Detecção de tipo ⏳ próxima

- [ ] `constants/signatures.py` — tabela de magic bytes
- [ ] `utils/signatures.py` — casador de assinatura, com `puremagic` como segunda opinião
- [ ] `services/evidence_detector.py` — classifica em `file` / `image` / `email`
- [ ] Regra de mismatch entre extensão declarada e assinatura real
- [ ] Testes, incluindo fixture de extensão falsa
- [ ] Adicionar `puremagic` ao `requirements.txt` e atualizar o README
- [ ] Corrigir a divergência do `python-magic` em `project-context.md`

---

## Etapa 4 — API de análise

**Primeira etapa com resultado visível:** dá para subir um arquivo pelo `/docs`
e receber o JSON da análise.

- [ ] `utils/temporary_files.py` — UUID, context manager, remoção garantida
- [ ] `schemas/analysis.py` — contrato Pydantic da resposta
- [ ] `analyzers/file_analyzer.py` — orquestra as etapas 2 e 3
- [ ] `POST /analyze` com limite de tamanho de upload
- [ ] Proteção contra path traversal
- [ ] Testes de upload e de limpeza dos temporários

---

## Etapa 5 — Risk Engine

- [ ] Modelo `Indicator`: `id`, `title`, `description`, `severity`, `score`, `evidence`
- [ ] `constants/risk_rules.py` — todos os pesos centralizados
- [ ] `services/risk_engine.py` — soma com teto de 100
- [ ] Faixas LOW / MEDIUM / HIGH / CRITICAL
- [ ] Testes das regras de pontuação

---

## Etapa 6 — Forense de imagem

- [ ] `analyzers/image_analyzer.py` com Pillow e exifread
- [ ] Dimensões, formato, modo de cor
- [ ] EXIF: dispositivo, modelo, software, timestamps
- [ ] GPS com conversão para coordenadas decimais
- [ ] Proteção contra *decompression bomb*
- [ ] Testes com imagens com e sem EXIF

---

## Etapa 7 — Forense de e-mail

- [ ] `analyzers/email_analyzer.py` — parser `.eml`
- [ ] Headers: From, To, Subject, Reply-To, Return-Path, Message-ID, Date
- [ ] Cadeia de `Received`
- [ ] `Authentication-Results`: SPF, DKIM, DMARC
- [ ] Mismatch entre From, Reply-To e Return-Path
- [ ] `analyzers/url_analyzer.py` — extração e heurísticas de URL
- [ ] Anexos com recursão limitada (profundidade 2, máximo 20)
- [ ] Testes com e-mail normal e e-mail suspeito

---

## Etapa 8 — Frontend do relatório

- [ ] `FileDropzone` com drag and drop
- [ ] `AnalysisLoading`
- [ ] `RiskScore` e `RiskBadge`
- [ ] `FileOverview`, `HashCard`, `MetadataCard`
- [ ] `ExifCard`
- [ ] `IndicatorsList`
- [ ] `EmailHeaders`, `AttachmentList`, `UrlList`
- [ ] `types/analysis.ts` espelhando os schemas Pydantic
- [ ] Abas variando conforme o tipo de evidência
- [ ] Tratamento visual de erro

---

## Etapa 9 — Relatórios e documentação

- [ ] Export JSON
- [ ] Relatório HTML standalone
- [ ] README completo com screenshots e arquitetura
- [ ] Seções de limitações, privacidade e segurança
- [ ] Disclaimer do Risk Score

---

## Divergências conhecidas na especificação

O [`project-context.md`](project-context.md) é o documento de concepção,
escrito antes de existir código. Alguns pontos já foram superados por decisões
posteriores. **Em caso de conflito, este roadmap e o
[`AGENTS.md`](../AGENTS.md) valem mais.**

| O documento diz | A decisão atual |
| --- | --- |
| Usar `python-magic` preferencialmente (seção 5) | Descartado — quebra no Windows. Tabela própria + `puremagic`. |
| Estrutura do backend (seção 7) | Não inclui `dev.py`, `pyproject.toml`, `requirements-dev.txt` nem `utils/streaming.py`. |
| Nada sobre ferramentas de qualidade | O projeto usa `ruff` e `httpx2`. |

---

## Fora do escopo

Banco de dados, autenticação, histórico, painel administrativo, IA/LLM,
VirusTotal obrigatório, sandbox, análise dinâmica, execução de macros, YARA,
Volatility, PCAP, Docker, CLI, filas, Redis, microserviços.
