/**
 * Dados estruturados em JSON-LD.
 *
 * Titulo e descricao dizem ao buscador como ESCREVER sobre a pagina. Isto diz
 * o que ela E: uma aplicacao de seguranca, gratuita, de codigo aberto, que
 * roda no navegador. E a diferenca entre aparecer como "mais um link azul" e
 * aparecer com o tipo, o preco e a plataforma ao lado.
 *
 * Por que um <script> aqui nao repete o problema do tema
 * ------------------------------------------------------
 * O <script> que aplica o tema no layout precisa EXECUTAR, e por isso o React
 * avisa quando o recria no cliente. Este nao executa nada: `application/ld+json`
 * e um tipo que o navegador nao interpreta, so carrega. Recria-lo e inofensivo,
 * e e assim que toda biblioteca de SEO faz.
 */

import { SITE_NAME, SITE_URL, REPOSITORY_URL } from "@/app/site";

export function StructuredData({
  locale,
  description,
}: {
  locale: string;
  description: string;
}) {
  const data = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: SITE_NAME,
    url: `${SITE_URL}/${locale}`,
    description,
    applicationCategory: "SecurityApplication",
    operatingSystem: "Any",
    inLanguage: locale,
    isAccessibleForFree: true,
    codeRepository: REPOSITORY_URL,
    /*
      `license` ficou de fora de proposito.
      A primeira versao declarava MIT, e isso era falso: o repositorio nao tem
      arquivo LICENSE, e sem ele o padrao legal e "todos os direitos
      reservados" - o oposto do que a marcacao afirmava.

      Para reativar, basta acrescentar um LICENSE ao repositorio e devolver a
      linha com a URL da licenca escolhida. Enquanto o arquivo nao existir, o
      campo correto e nenhum.
    */
    author: {
      "@type": "Person",
      name: "Vinicius Rampazzo",
      url: REPOSITORY_URL,
    },
    // Declarar o preco como zero e o que permite ao buscador mostrar
    // "gratuito". Sem a oferta, ele nao assume.
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
    },
  };

  return (
    <script
      type="application/ld+json"
      // O conteudo e montado por nos a partir de constantes e da traducao.
      // Nenhum dado de usuario entra nesta string.
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
