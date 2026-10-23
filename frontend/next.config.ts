import createNextIntlPlugin from "next-intl/plugin";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
};

// O plugin ensina ao Next onde esta a configuracao de idioma (`i18n/request.ts`)
// e habilita o uso das traducoes dentro de Server Components.
const withNextIntl = createNextIntlPlugin();

export default withNextIntl(nextConfig);
