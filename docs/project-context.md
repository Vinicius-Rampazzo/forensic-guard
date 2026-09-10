# ForensicGuard — Contexto Técnico e Arquitetura do Projeto

## 1. Visão geral

O **ForensicGuard** será uma aplicação open source de análise forense e triagem de evidências digitais.

O objetivo principal é permitir que o usuário envie um arquivo, uma imagem ou um e-mail em formato `.eml` e receba uma análise técnica contendo informações sobre o arquivo, metadados, assinaturas, hashes, indicadores suspeitos e um nível de risco estimado.

A aplicação deverá ser simples, local-first, sem banco de dados, sem autenticação e sem armazenamento permanente das evidências analisadas.

O projeto será desenvolvido com foco em portfólio de Cybersecurity / Digital Forensics, priorizando código limpo, arquitetura modular, boa documentação e interface profissional.

A aplicação não deverá afirmar que um arquivo é definitivamente malware. O sistema fará apenas uma **triagem técnica baseada em indicadores e heurísticas**.

---

# 2. Objetivo do projeto

Criar uma ferramenta capaz de responder à seguinte pergunta:

> "Esta evidência digital apresenta características técnicas que merecem atenção?"

O sistema deverá analisar três categorias principais:

1. Arquivos em geral
2. Imagens
3. E-mails `.eml`

Dependendo do tipo enviado, módulos específicos serão executados automaticamente.

---

# 3. Princípios do projeto

O projeto deverá seguir os seguintes princípios:

- Open source
- Sem banco de dados
- Sem autenticação
- Sem cadastro de usuário
- Sem armazenamento permanente
- Sem dependência obrigatória de serviços externos
- Sem necessidade de API keys no MVP
- Evidências processadas temporariamente
- Arquivos removidos após o processamento
- Código modular
- Analisadores independentes
- API desacoplada do frontend
- Fácil instalação local
- Fácil demonstração em portfólio

A aplicação deverá poder ser clonada do GitHub e executada localmente sem configuração de banco.

---

# 4. Stack definida

## Frontend

- Next.js 16
- React
- TypeScript
- Tailwind CSS

Responsabilidades do frontend:

- Upload de evidências
- Drag and drop de arquivos
- Exibição do resultado
- Indicador visual de risco
- Exibição de hashes
- Exibição de metadados
- Exibição de indicadores encontrados
- Exibição de informações específicas de e-mail
- Exibição de informações EXIF
- Exportação do relatório
- Feedback de processamento
- Tratamento visual de erros

---

## Backend

- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic

Responsabilidades do backend:

- Receber os arquivos
- Identificar o tipo de evidência
- Salvar temporariamente o arquivo quando necessário
- Executar os analisadores
- Normalizar os resultados
- Calcular o Risk Score
- Retornar JSON para o frontend
- Excluir arquivos temporários

---

# 5. Bibliotecas Python previstas

## Hashes

Utilizar:

```python
hashlib
```

Calcular inicialmente:

- MD5
- SHA-1
- SHA-256
- SHA-512

---

## Identificação de arquivos

Utilizar preferencialmente:

- `python-magic`
- leitura manual de magic bytes quando necessário

Objetivo:

Comparar:

- extensão informada
- MIME type
- assinatura real do arquivo

Exemplo:

```text
Arquivo:
foto.jpg

Extensão:
.jpg

MIME declarado:
image/jpeg

Assinatura real:
PE32 executable

Resultado:
CRITICAL — File extension mismatch
```

---

## EXIF e imagens

Bibliotecas possíveis:

- Pillow
- exifread

Informações que poderão ser extraídas:

- fabricante do dispositivo
- modelo
- data de criação
- data de modificação
- software utilizado
- orientação
- resolução
- coordenadas GPS
- câmera
- lente
- informações adicionais disponíveis

A ausência de EXIF não deve ser considerada automaticamente suspeita.

---

## E-mails

Utilizar inicialmente a biblioteca nativa:

```python
email
```

Informações a extrair:

- From
- To
- Subject
- Date
- Message-ID
- Reply-To
- Return-Path
- Received
- Authentication-Results
- SPF, quando presente
- DKIM, quando presente
- DMARC, quando presente
- anexos
- URLs
- domínios
- endereços IP

O sistema deverá analisar inconsistências entre os headers.

Exemplo:

```text
From:
security@empresa.com

Reply-To:
empresa-security@gmail.com

Indicador:
Sender / Reply-To mismatch
```

---

# 6. Arquitetura geral

Fluxo principal:

```text
Frontend Next.js
        |
        v
FastAPI
        |
        v
Evidence Detector
        |
        +-------------------+
        |                   |
        v                   v
File Analyzer          Email Analyzer
        |
        v
Image Analyzer
        |
        v
Indicator Engine
        |
        v
Risk Engine
        |
        v
Normalized JSON
        |
        v
Frontend Report
```

---

# 7. Estrutura inicial do backend

Estrutura sugerida:

```text
backend/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   └── routes/
│   │       └── analysis.py
│   │
│   ├── analyzers/
│   │   ├── file_analyzer.py
│   │   ├── image_analyzer.py
│   │   ├── email_analyzer.py
│   │   ├── url_analyzer.py
│   │   └── string_analyzer.py
│   │
│   ├── services/
│   │   ├── evidence_detector.py
│   │   ├── risk_engine.py
│   │   └── report_service.py
│   │
│   ├── utils/
│   │   ├── hashing.py
│   │   ├── entropy.py
│   │   ├── signatures.py
│   │   ├── temporary_files.py
│   │   └── extractors.py
│   │
│   ├── schemas/
│   │   └── analysis.py
│   │
│   └── constants/
│       ├── signatures.py
│       └── risk_rules.py
│
├── tests/
│
├── requirements.txt
└── README.md
```

---

# 8. Estrutura inicial do frontend

Estrutura sugerida:

```text
frontend/
│
├── app/
│   ├── page.tsx
│   │
│   ├── analyze/
│   │
│   └── report/
│
├── components/
│   ├── FileDropzone.tsx
│   ├── AnalysisLoading.tsx
│   ├── RiskScore.tsx
│   ├── RiskBadge.tsx
│   ├── FileOverview.tsx
│   ├── HashCard.tsx
│   ├── MetadataCard.tsx
│   ├── ExifCard.tsx
│   ├── IndicatorsList.tsx
│   ├── EmailHeaders.tsx
│   ├── AttachmentList.tsx
│   └── UrlList.tsx
│
├── services/
│   └── api.ts
│
├── types/
│   └── analysis.ts
│
└── utils/
```

---

# 9. Fluxo de análise

Quando um arquivo for enviado:

```text
Upload
   ↓
Validação inicial
   ↓
Arquivo temporário
   ↓
Identificação do tipo
   ↓
Análise genérica
   ↓
Análise específica
   ↓
Extração de indicadores
   ↓
Risk Engine
   ↓
Resultado JSON
   ↓
Remoção do arquivo temporário
```

---

# 10. File Analyzer

Todos os arquivos enviados devem passar pelo File Analyzer.

Funções principais:

## Informações básicas

Extrair:

- nome
- extensão
- tamanho
- MIME
- tipo real
- assinatura
- timestamps disponíveis

---

## Hashes

Calcular:

```text
MD5
SHA1
SHA256
SHA512
```

O SHA-256 será o principal identificador exibido.

---

## File signature

O sistema deverá verificar os primeiros bytes do arquivo.

Exemplo de assinaturas:

```text
PDF
25 50 44 46

JPEG
FF D8 FF

PNG
89 50 4E 47

ZIP
50 4B 03 04

Windows PE
4D 5A
```

Deverá existir comparação entre assinatura e extensão.

---

# 11. Entropy Analyzer

Calcular entropia de Shannon.

Objetivo:

Identificar arquivos ou regiões com conteúdo altamente aleatório.

Exemplo:

```text
Entropy:
7.91 / 8.00

Indicator:
High entropy
```

Entropia alta pode estar relacionada a:

- compressão
- criptografia
- packing
- conteúdo binário

Nunca deverá ser tratada isoladamente como evidência de malware.

---

# 12. String Analyzer

Extrair strings ASCII e Unicode relevantes.

O sistema poderá procurar:

- URLs
- domínios
- IPv4
- IPv6
- e-mails
- caminhos Windows
- comandos PowerShell
- referências a CMD
- executáveis
- caminhos temporários

Exemplos:

```text
powershell.exe
cmd.exe
C:\Users\Public\
https://example.com
192.168.1.10
```

Essas informações deverão ser apresentadas como artefatos encontrados.

---

# 13. Image Forensics

Se o tipo identificado for imagem, executar análise específica.

Formatos iniciais:

```text
JPG
JPEG
PNG
TIFF
WEBP
```

Extrair:

- resolução
- formato
- modo de cor
- EXIF
- GPS
- fabricante
- modelo
- data
- software

Exemplo:

```text
Device:
Apple iPhone 15 Pro

Software:
Adobe Photoshop 25.1

GPS:
Present

Coordinates:
-22.1200, -51.3900
```

GPS deve ser tratado principalmente como informação de privacidade/metadata, não necessariamente como indicador malicioso.

---

# 14. Email Forensics

Arquivos `.eml` deverão passar por um pipeline específico.

Fluxo:

```text
.eml
 ↓
Parser
 ↓
Headers
 ↓
Authentication
 ↓
URLs
 ↓
Attachments
 ↓
Indicators
```

---

## Headers

Analisar:

```text
From
To
Subject
Reply-To
Return-Path
Message-ID
Date
Received
Authentication-Results
```

---

## Sender mismatch

Comparar:

- domínio de `From`
- domínio de `Reply-To`
- domínio de `Return-Path`

Exemplo:

```text
From:
financeiro@empresa.com

Reply-To:
empresa.financeiro@gmail.com

Indicator:
Reply-To domain differs from sender
```

Essa diferença não deverá automaticamente classificar o e-mail como phishing.

---

## Authentication

Se os headers contiverem os resultados, extrair:

```text
SPF
DKIM
DMARC
```

Exemplo:

```text
SPF:
fail

DKIM:
fail

DMARC:
fail
```

Isso deverá impactar o Risk Score.

O MVP não deverá obrigatoriamente realizar consultas DNS externas para validar novamente os protocolos.

---

# 15. URLs

Extrair URLs de:

- corpo HTML
- corpo texto
- headers
- anexos textuais, quando seguro

Informações iniciais:

```text
URL
Protocol
Hostname
Domain
Path
```

Possíveis indicadores heurísticos:

- endereço IP no lugar do domínio
- domínio em punycode
- quantidade anormal de subdomínios
- URLs muito longas
- presença de `@`
- uso de encurtadores conhecidos
- HTTP sem TLS
- domínio diferente do remetente

Importante:

Uma URL heurísticamente suspeita não significa que seja maliciosa.

---

# 16. Attachments

Anexos extraídos de `.eml` deverão ser analisados automaticamente.

Exemplo:

```text
phishing.eml
   |
   +-- invoice.pdf
   |
   +-- logo.png
```

Cada anexo poderá passar pelo File Analyzer.

Caso seja imagem:

```text
File Analyzer
      ↓
Image Analyzer
```

Isso cria análise recursiva controlada.

---

# 17. Limites da análise recursiva

É necessário impedir abuso ou loops.

Definir inicialmente:

```text
max_attachment_depth = 2
max_attachments = 20
max_file_size = configurable
```

Arquivos compactados não precisam ser extraídos automaticamente no MVP.

---

# 18. Risk Engine

O Risk Engine receberá os indicadores encontrados e calculará uma pontuação.

Exemplo de faixas:

```text
0 - 20
LOW

21 - 50
MEDIUM

51 - 75
HIGH

76 - 100
CRITICAL
```

Pontuação máxima:

```text
100
```

---

# 19. Regras iniciais de risco

Exemplos de regras:

```text
Executable disguised as another extension
+50

Extension / signature mismatch
+35

SPF fail
+15

DKIM fail
+10

DMARC fail
+15

Reply-To mismatch
+10

Return-Path mismatch
+10

IP-based URL
+15

Punycode domain
+15

Suspicious PowerShell string
+20

High entropy
+10

Unexpected executable attachment
+30
```

Os valores deverão ficar centralizados em:

```text
risk_rules.py
```

Nunca espalhar magic numbers pelo código.

---

# 20. Explicabilidade

Todo indicador deverá possuir:

```text
id
title
description
severity
score
evidence
```

Exemplo:

```json
{
  "id": "file.extension_mismatch",
  "title": "File extension mismatch",
  "description": "The filename extension does not match the detected file signature.",
  "severity": "high",
  "score": 35,
  "evidence": {
    "extension": ".jpg",
    "detected_type": "PE32 executable"
  }
}
```

Isso é importante porque o usuário precisa entender por que determinado score foi atribuído.

---

# 21. Resultado da API

Resposta aproximada:

```json
{
  "filename": "invoice.jpg",
  "file": {
    "size": 84921,
    "extension": ".jpg",
    "mime": "application/x-dosexec",
    "detected_type": "PE32 executable",
    "entropy": 7.61,
    "hashes": {
      "md5": "...",
      "sha1": "...",
      "sha256": "...",
      "sha512": "..."
    }
  },
  "risk": {
    "score": 85,
    "level": "critical"
  },
  "indicators": [
    {
      "id": "file.extension_mismatch",
      "severity": "high",
      "score": 35
    }
  ]
}
```

O schema definitivo deverá ser modelado utilizando Pydantic.

---

# 22. Interface

A interface deverá ser minimalista, profissional e voltada para Cybersecurity.

Tela inicial:

```text
ForensicGuard

Digital Evidence Analyzer

Drop evidence here

JPG • PNG • PDF • EML • DOCX • EXE ...

[ Select File ]
```

Após análise:

```text
FILE ANALYSIS

invoice.jpg

Risk Score
85 / 100
CRITICAL

Overview
Hashes
Metadata
Indicators
Strings
```

Para imagem:

```text
Overview
Hashes
EXIF
Location
Indicators
```

Para e-mail:

```text
Overview
Headers
Authentication
URLs
Attachments
Indicators
```

---

# 23. Relatório

O usuário poderá exportar o resultado.

MVP:

- JSON
- HTML
- TXT opcional

O HTML deverá funcionar como relatório standalone.

---

# 24. Privacidade

Uma característica importante do projeto será a ausência de armazenamento.

Mensagem recomendada:

```text
Privacy First

No database
No account required
No permanent evidence storage
Files are removed after processing
Designed to run locally
```

---

# 25. Arquivos temporários

Nunca confiar diretamente no nome enviado pelo usuário.

Gerar identificador interno seguro.

Exemplo:

```text
/tmp/forensicguard/UUID
```

Após processamento:

```text
try:
    analyze()
finally:
    delete_temp_file()
```

A remoção deverá acontecer mesmo em caso de exceção.

---

# 26. Segurança da própria aplicação

Como a aplicação processará arquivos potencialmente hostis, o código deverá assumir que qualquer upload é não confiável.

Regras:

- nunca executar arquivos enviados
- nunca importar código do arquivo analisado
- nunca executar macros
- nunca abrir executáveis
- limitar tamanho dos uploads
- validar conteúdo
- usar nomes temporários seguros
- impedir path traversal
- evitar shell commands quando possível
- quando shell for necessário, nunca usar entrada do usuário sem escaping
- aplicar timeout em operações pesadas
- limitar análise recursiva
- excluir temporários
- tratar exceções de parsers

---

# 27. O que NÃO fará parte do MVP

Não implementar inicialmente:

- banco de dados
- Supabase
- PostgreSQL
- Firebase
- autenticação
- login
- cadastro
- histórico de análises
- painel administrativo
- IA generativa
- LLM
- VirusTotal obrigatório
- sandbox de execução
- detonação de malware
- análise dinâmica
- execução de macros
- Volatility
- análise de memória RAM
- PCAP
- YARA obrigatório
- consultas externas obrigatórias

---

# 28. MVP

O MVP deverá possuir:

## Upload

- drag and drop
- seleção manual
- validação de tamanho

## Arquivos

- nome
- extensão
- MIME
- magic bytes
- assinatura
- tamanho
- MD5
- SHA1
- SHA256
- SHA512
- entropia
- strings básicas

## Imagens

- dimensões
- formato
- EXIF
- dispositivo
- software
- timestamps
- GPS

## E-mails

- headers principais
- Received
- Reply-To
- Return-Path
- Authentication-Results
- SPF
- DKIM
- DMARC
- URLs
- anexos

## Risk Engine

- indicadores
- score
- classificação
- explicações

## Relatório

- visualização web
- JSON
- HTML

---

# 29. Roadmap

## V1 — Core

Criar:

```text
FastAPI
Upload
File Analyzer
Hashing
Signature Detection
Risk Engine inicial
Frontend básico
```

---

## V1.1 — Image Forensics

Adicionar:

```text
Image Detector
EXIF
GPS
Camera metadata
Software metadata
Image report
```

---

## V1.2 — Email Forensics

Adicionar:

```text
EML parser
Headers
Authentication-Results
URLs
Attachments
Sender mismatch analysis
```

---

## V1.3 — Reporting

Adicionar:

```text
JSON export
HTML report
Melhorias na UI
Indicadores explicáveis
```

---

# 30. Possíveis funcionalidades futuras

Após o MVP estar completo e estável, avaliar:

- PDF structural analysis
- QR Code extraction
- YARA
- VirusTotal opcional
- WHOIS
- DNS lookup
- domain age
- SSL certificate inspection
- archive inspection
- Office document metadata
- macros detection
- PE static analysis
- favicon/hash analysis
- URL reputation
- STIX export
- IOC export
- CLI
- Docker

Todas essas funcionalidades deverão ser opcionais e adicionadas somente depois da arquitetura principal estar consolidada.

---

# 31. Possível modo CLI

No futuro, disponibilizar:

```bash
forensicguard analyze suspicious.eml
```

Resultado:

```text
ForensicGuard

File:
suspicious.eml

Risk:
HIGH — 72/100

Indicators:
[HIGH] SPF failed
[MEDIUM] Reply-To mismatch
[MEDIUM] Suspicious URL
[LOW] HTML-only email
```

Isso aumentaria o valor do projeto para profissionais de segurança.

---

# 32. Filosofia do Risk Score

O Risk Score é uma heurística.

Nunca utilizar mensagens como:

```text
This file is malware.
```

Preferir:

```text
This file contains indicators commonly associated with suspicious files.
```

Ou:

```text
Potentially suspicious evidence detected.
```

Adicionar disclaimer:

> The ForensicGuard risk score is based on static indicators and heuristics. It does not provide a definitive malware or phishing verdict.

---

# 33. Testes

Criar testes unitários principalmente para:

- hashing
- entropy
- magic bytes
- MIME detection
- URL extraction
- sender mismatch
- risk score
- EXIF parsing
- EML parsing

Utilizar:

```text
pytest
```

Criar arquivos controlados dentro de:

```text
tests/fixtures/
```

Nunca colocar malware real no repositório.

---

# 34. Fixtures seguras

Exemplos:

```text
sample.jpg
sample-with-exif.jpg
sample.pdf
normal-email.eml
suspicious-email.eml
fake-extension.jpg
```

O arquivo `fake-extension.jpg` poderá ser um arquivo inofensivo criado especificamente para testar mismatch de assinatura.

---

# 35. README

O README deverá explicar:

- objetivo
- screenshots
- funcionalidades
- arquitetura
- instalação
- execução
- exemplos
- limitações
- privacidade
- segurança
- roadmap

Headline sugerida:

```text
ForensicGuard

Lightweight Digital Evidence Analyzer
```

Descrição:

> Open-source forensic triage tool for inspecting files, images and emails for suspicious indicators, metadata anomalies and potential security threats.

Badges possíveis:

```text
Python
FastAPI
Next.js
TypeScript
Digital Forensics
Open Source
```

---

# 36. Diferencial do projeto

O diferencial não será inventar técnicas forenses novas.

O objetivo é reunir técnicas conhecidas em uma ferramenta:

- simples
- visual
- modular
- explicável
- privacy-first
- fácil de executar
- útil para aprendizado
- adequada para portfólio

A ferramenta deverá mostrar conhecimento prático em:

- Digital Forensics
- Cybersecurity
- análise estática
- manipulação segura de arquivos
- protocolos de e-mail
- hashing
- metadata
- APIs
- arquitetura backend
- frontend moderno
- segurança de software

---

# 37. Escopo técnico final

Stack:

```text
Frontend
Next.js + React + TypeScript + Tailwind

Backend
Python + FastAPI + Pydantic + Uvicorn

Forensics
hashlib
python-magic
Pillow
exifread
email
regex
urllib
math

Tests
pytest

Persistence
None
```

Arquitetura:

```text
Stateless
No Database
No Authentication
Temporary Processing
Local-first
API REST
```

---

# 38. Resultado esperado

Ao final do MVP, deverá ser possível:

1. abrir a aplicação
2. arrastar um arquivo
3. iniciar análise
4. identificar automaticamente o tipo
5. executar módulos compatíveis
6. calcular hashes
7. analisar assinatura
8. extrair metadata
9. analisar EXIF se aplicável
10. analisar `.eml` se aplicável
11. analisar URLs
12. analisar anexos
13. gerar indicadores
14. calcular Risk Score
15. explicar o resultado
16. exibir relatório
17. exportar JSON ou HTML
18. apagar a evidência temporária

Sem banco de dados e sem persistência permanente.

---

# 39. Diretriz para o agente de IA

Durante o desenvolvimento, não adicionar complexidade fora deste escopo sem necessidade.

Priorizar:

```text
simplicidade
modularidade
tipagem
testabilidade
segurança
legibilidade
documentação
```

Antes de implementar qualquer funcionalidade nova, verificar se ela realmente pertence ao MVP.

Não adicionar automaticamente:

```text
database
authentication
cloud storage
AI
LLM
microservices
message queues
Redis
Docker
external APIs
```

O projeto deve permanecer pequeno o suficiente para ser desenvolvido e mantido como projeto pessoal, mas tecnicamente sólido o suficiente para demonstrar conhecimentos reais de Digital Forensics e Cybersecurity.
