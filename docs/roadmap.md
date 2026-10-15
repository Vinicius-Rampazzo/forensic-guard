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
| **Última etapa concluída** | Etapa 5 — Risk Engine |
| **Próxima etapa** | Etapa 6 — Forense de imagem |
| **Já funciona ponta a ponta** | `POST /analyze` devolve hashes, entropia, tipo detectado, mismatch, artefatos, **Risk Score e indicadores explicáveis**. Experimente em `/docs`. |
| **Testes** | 194, todos passando |

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

## Etapa 3 — Detecção de tipo ✅

Branch: `feat/type-detection`

- [x] `constants/signatures.py` — tabela com 33 formatos, suporte a múltiplos padrões por formato e offsets diferentes de zero
- [x] `utils/signatures.py` — casador por especificidade, com `puremagic` como segunda opinião
- [x] `services/evidence_detector.py` — classifica em `file` / `image` / `email`
- [x] Regra de mismatch, distinguindo `executable_disguised` de `type_mismatch`
- [x] Tratamento de extensões alternativas (`.jpeg`) e formatos contêiner (`.docx` é ZIP)
- [x] Detecção de `.eml` por heurística de cabeçalhos, independente da extensão
- [x] 56 testes novos (101 no total)
- [x] `puremagic==2.2.0` no `requirements.txt` e README atualizado
- [x] Divergência do `python-magic` corrigida em `project-context.md`

---

## Etapa 4 — API de análise ✅

Branch: `feat/type-detection` *(as etapas 3 e 4 fecharam na mesma branch, por
decisão do Vinicius)*

**Primeira etapa com resultado visível:** dá para subir um arquivo pelo `/docs`
e receber o JSON da análise.

- [x] `utils/temporary_files.py` — nome por UUID, context manager, remoção em `finally`
- [x] Limite de upload verificado durante a escrita, com remoção do arquivo parcial
- [x] `schemas/analysis.py` — contrato Pydantic da resposta
- [x] `analyzers/file_analyzer.py` — fatos genéricos do arquivo
- [x] `services/analysis_service.py` — orquestra detector + analisador *(não previsto; necessário para respeitar as camadas)*
- [x] `POST /analyze`, rota síncrona executada em pool de threads
- [x] Proteção contra path traversal no nome do upload
- [x] 34 testes novos (135 no total), incluindo o de "nada fica em disco"
- [x] `python-multipart==0.0.32` no `requirements.txt` e README atualizado

---

## Etapa 5 — Risk Engine ✅

Branch: `feat/type-detection` *(etapas 3, 4 e 5 fecharam na mesma branch, por
decisão do Vinicius)*

- [x] Modelo `Indicator`: regra que disparou + evidência que a justificou
- [x] `constants/risk_rules.py` — 7 regras, pesos, severidades e faixas centralizados
- [x] `services/indicator_engine.py` — traduz fatos em indicadores *(separado do risk_engine, como na especificação)*
- [x] `services/risk_engine.py` — soma com teto de 100 e classificação
- [x] `analyzers/url_analyzer.py` — URL por IP e domínio punycode *(antecipado da Etapa 7, só a parte necessária)*
- [x] Entropia alta só gera indicador quando inesperada para o formato
- [x] Faixas LOW / MEDIUM / HIGH / CRITICAL, com testes em cada borda
- [x] 59 testes novos (194 no total)
- [x] README com a seção "How the risk score works"

---

## Etapa 6 — Forense de imagem ⏳ próxima

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
| ~~Usar `python-magic`~~ | ✅ corrigido no documento na Etapa 3. |
| Estrutura do backend (seção 7) | Não inclui `dev.py`, `pyproject.toml`, `requirements-dev.txt` nem `utils/streaming.py`. |
| Nada sobre ferramentas de qualidade | O projeto usa `ruff` e `httpx2`. |
| Formatos suportados (seção 13) | A tabela de assinaturas cobre 33 formatos, incluindo executáveis Linux/macOS, SQLite e atalhos `.lnk`. |

---

## Fora do escopo

Banco de dados, autenticação, histórico, painel administrativo, IA/LLM,
VirusTotal obrigatório, sandbox, análise dinâmica, execução de macros, YARA,
Volatility, PCAP, Docker, CLI, filas, Redis, microserviços.
