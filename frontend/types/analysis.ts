/**
 * Tipos da resposta de analise.
 *
 * Este arquivo e o espelho em TypeScript de `backend/app/schemas/analysis.py`.
 * Os nomes dos campos estao em snake_case de proposito: sao exatamente as
 * chaves que chegam no JSON, e renomear aqui criaria uma camada de traducao
 * que so serviria para esconder divergencias.
 *
 * ATENCAO: nenhuma ferramenta verifica se os dois lados continuam iguais. Se
 * um schema Pydantic mudar, este arquivo precisa mudar junto, na mesma leva.
 * Por isso os tipos ficam todos aqui, e nao espalhados pelos componentes -
 * quando a API mudar, existe um unico lugar para atualizar.
 */

/** Familia de evidencia, define quais abas o relatorio exibe. */
export type EvidenceType = "file" | "image" | "email";

/** Tipo de contradicao entre o nome declarado e o conteudo real. */
export type MismatchKind = "none" | "type_mismatch" | "executable_disguised";

/** Gravidade de um indicador isolado. */
export type Severity = "info" | "low" | "medium" | "high" | "critical";

/** Classificacao final da evidencia. */
export type RiskLevel = "low" | "medium" | "high" | "critical";

/** Familia do formato reconhecido pelos magic bytes. */
export type FileCategory =
  | "image"
  | "document"
  | "archive"
  | "executable"
  | "media"
  | "email"
  | "database"
  | "other";

export interface Hashes {
  md5: string;
  sha1: string;
  sha256: string;
  sha512: string;
}

export interface FileOverview {
  size: number;
  /** Entropia de Shannon, de 0 a 8. Acima de 7,5 indica compressao ou cifragem. */
  entropy: number;
  hashes: Hashes;
}

/** Padroes de interesse forense encontrados nas strings. */
export interface Artifacts {
  urls?: string[];
  ipv4?: string[];
  ipv6?: string[];
  emails?: string[];
  windows_paths?: string[];
  suspicious_keywords?: string[];
}

export interface StringsAnalysis {
  /** Quantas strings existem de fato - contado antes de qualquer corte. */
  total: number;
  /** Quantas vieram na amostra abaixo. */
  returned: number;
  /**
   * Verdadeiro quando um limite cortou a LISTAGEM de strings.
   *
   * Nao significa que o arquivo deixou de ser examinado: hashes, entropia,
   * deteccao de tipo e os artefatos cobrem o arquivo inteiro.
   */
  truncated: boolean;
  /** Qual limite foi atingido, em linguagem comum. */
  truncation_reason: string | null;
  sample: string[];
  artifacts: Artifacts;
}

export interface Detection {
  evidence_type: EvidenceType;
  declared_extension: string;
  detected_name: string | null;
  detected_mime: string | null;
  detected_category: FileCategory | null;
  /** Quantos bytes sustentam a conclusao. Dois e evidencia fraca, oito e forte. */
  confirmed_bytes: number;
  ambiguous_with: string[];
  puremagic_mime: string | null;
  second_opinion_agrees: boolean | null;
  mismatch: MismatchKind;
  notes: string[];
}

export interface Gps {
  latitude: number;
  longitude: number;
}

export interface ImageAnalysis {
  width: number | null;
  height: number | null;
  megapixels: number | null;
  image_format: string | null;
  color_mode: string | null;
  device_make: string | null;
  device_model: string | null;
  software: string | null;
  created_at: string | null;
  gps: Gps | null;
  exif: Record<string, string>;
  error: string | null;
}

export interface Authentication {
  spf: string | null;
  dkim: string | null;
  dmarc: string | null;
  raw: string | null;
}

export interface EmailLink {
  /** Para onde o link realmente aponta. */
  url: string;
  /** O que o destinatario enxerga. */
  display_text: string;
  misleading: boolean;
}

export interface Attachment {
  filename: string;
  declared_content_type: string;
  size: number;
  /**
   * Analise completa do anexo - recursiva, com Risk Score proprio.
   * Nula quando o limite de profundidade impediu a analise.
   */
  analysis: AnalysisResult | null;
}

export interface EmailAnalysis {
  headers: Record<string, string>;
  from_address: string | null;
  from_domain: string | null;
  reply_to: string | null;
  reply_to_domain: string | null;
  return_path: string | null;
  return_path_domain: string | null;
  reply_to_mismatch: boolean;
  return_path_mismatch: boolean;
  received_chain: string[];
  authentication: Authentication;
  has_text_body: boolean;
  has_html_body: boolean;
  urls: string[];
  links: EmailLink[];
  attachments: Attachment[];
  attachments_truncated: boolean;
  error: string | null;
}

export interface Indicator {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  score: number;
  /** Os dados concretos que dispararam a regra. Formato varia por indicador. */
  evidence: Record<string, unknown>;
}

export interface Risk {
  score: number;
  level: RiskLevel;
  indicators: Indicator[];
}

export interface AnalysisResult {
  filename: string;
  file: FileOverview;
  detection: Detection;
  strings: StringsAnalysis;
  risk: Risk;
  /** Presente apenas quando a evidencia e uma imagem. */
  image: ImageAnalysis | null;
  /** Presente apenas quando a evidencia e um e-mail. */
  email: EmailAnalysis | null;
  disclaimer: string;
}
