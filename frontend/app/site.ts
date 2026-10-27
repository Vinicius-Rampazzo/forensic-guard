/**
 * Endereco publico do site.
 *
 * Buscadores e redes sociais exigem URL ABSOLUTA. Caminho relativo nao serve:
 * quem monta o cartao de preview e um servidor do Facebook ou do LinkedIn, que
 * nao tem como resolver `/og.png` contra nada.
 *
 * Vem de variavel de ambiente para que o deploy de producao, os previews da
 * Vercel e a maquina de quem clonou nao fiquem todos se anunciando com o mesmo
 * endereco. `NEXT_PUBLIC_SITE_URL` nao e segredo - ja esta estampado na barra
 * do navegador.
 *
 * A barra final e removida sempre. Com ela, `${SITE_URL}/pt-br` viraria
 * `https://exemplo.com//pt-br`, que funciona por acidente mas aparece feio em
 * canonical e sitemap.
 */

export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? "https://forensic-guard-rspd.vercel.app"
).replace(/\/+$/, "");

export const SITE_NAME = "ForensicGuard";

/** Repositorio, usado nos dados estruturados. */
export const REPOSITORY_URL = "https://github.com/Vinicius-Rampazzo/forensic-guard";
