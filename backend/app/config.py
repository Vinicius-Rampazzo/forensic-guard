"""Configuracao da aplicacao.

Toda configuracao vem de variaveis de ambiente, nunca de constante escrita no
meio do codigo. Isso permite que a mesma imagem do projeto rode em maquinas
diferentes (sua maquina, a de outro dev, um servidor) mudando apenas o .env.

pydantic-settings faz o trabalho pesado: le o .env, converte os tipos e valida.
Se MAX_UPLOAD_SIZE vier como "abc", a aplicacao falha ao subir com uma mensagem
clara - e nao la na frente, no meio de um upload.
"""

import tempfile
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz da pasta backend/, calculada a partir deste arquivo.
# Usamos caminho absoluto porque o .env precisa ser encontrado independentemente
# de qual diretorio o usuario estava quando rodou o uvicorn.
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configuracao tipada da aplicacao.

    Cada atributo pode ser sobrescrito por uma variavel de ambiente de mesmo
    nome, em maiusculas. Exemplo: `app_name` <- `APP_NAME`.
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignora variaveis desconhecidas em vez de quebrar
    )

    app_name: str = "ForensicGuard"
    version: str = "0.1.0"

    # Origens autorizadas a chamar a API pelo navegador (CORS).
    # Guardado como string separada por virgula em vez de list[str] porque
    # pydantic-settings espera JSON para tipos complexos vindos do ambiente -
    # e escrever '["http://localhost:3000"]' num .env e desconfortavel.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Limite de upload. Existe por seguranca, nao por conveniencia: sem limite,
    # um unico arquivo gigante derruba o servico (negacao de servico).
    max_upload_size: int = 25 * 1024 * 1024  # 25 MB

    # Onde as evidencias sao gravadas enquanto estao sendo analisadas.
    # Nada persiste aqui: cada arquivo e apagado ao fim da analise.
    temp_dir: Path = Path(tempfile.gettempdir()) / "forensicguard"

    @property
    def cors_origins_list(self) -> list[str]:
        """Converte a string de origens na lista que o middleware espera."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devolve a configuracao da aplicacao.

    O lru_cache garante que o .env seja lido do disco uma unica vez por
    processo. Todas as chamadas seguintes recebem o mesmo objeto.
    """
    return Settings()
