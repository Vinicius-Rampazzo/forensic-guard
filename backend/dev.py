#!/usr/bin/env python3
"""Executor de tarefas do backend do ForensicGuard.

Motivacao
---------
O Node tem um executor de tarefas embutido: o bloco "scripts" do package.json,
que permite escrever `npm run dev`. O Python nao tem equivalente nativo - pip
instala pacotes, venv isola ambientes, mas nada executa tarefas. O resultado e
o comando longo que voce precisaria digitar a mao:

    backend\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --app-dir backend

Este arquivo e o equivalente do `npm run dev` para o nosso backend:

    python dev.py            sobe o servidor de desenvolvimento
    python dev.py test       roda os testes
    python dev.py lint       roda o ruff
    python dev.py format     formata o codigo com o ruff
    python dev.py check      lint + testes (util antes de commitar)
    python dev.py install    apenas prepara o ambiente, sem executar nada

Como ele dispensa a ativacao do venv
------------------------------------
Ao ser chamado com o Python do sistema, o script percebe que nao esta dentro do
venv, garante que o ambiente existe e entao **chama a si mesmo de novo** usando
o Python de dentro do venv. Quem digitou o comando nao precisa saber que isso
aconteceu.

Nao depende de nenhuma biblioteca externa - apenas da biblioteca padrao - para
que funcione mesmo num clone recem-feito, antes de qualquer instalacao.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Todos os caminhos sao derivados da localizacao deste arquivo, nunca do
# diretorio em que o usuario estava ao rodar o comando. Assim o script funciona
# tanto de dentro de backend/ quanto da raiz do projeto.
BACKEND_DIR = Path(__file__).resolve().parent
VENV_DIR = BACKEND_DIR / ".venv"
REQUIREMENTS = BACKEND_DIR / "requirements.txt"
REQUIREMENTS_DEV = BACKEND_DIR / "requirements-dev.txt"

# Arquivo-marcador gravado apos cada instalacao bem-sucedida. Comparando a data
# dele com a dos requirements, o script descobre se as dependencias mudaram
# desde a ultima vez - e reinstala sozinho quando alguem edita o requirements.
DEPS_STAMP = VENV_DIR / ".deps-stamp"

MINIMUM_PYTHON = (3, 12)
IS_WINDOWS = os.name == "nt"


# ---------------------------------------------------------------------------
# Saida no terminal
# ---------------------------------------------------------------------------


# flush=True e obrigatorio aqui. Quando a saida do script vai para um pipe em
# vez de um terminal (log de CI, saida redirecionada), o print do Python fica
# em buffer enquanto a saida dos subprocessos vai direto - e as mensagens
# aparecem fora de ordem.


def info(message: str) -> None:
    print(f"  {message}", flush=True)


def step(message: str) -> None:
    print(f"\n> {message}", flush=True)


def fail(message: str) -> None:
    print(f"\nERROR: {message}\n", file=sys.stderr, flush=True)
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# Ambiente virtual
# ---------------------------------------------------------------------------


def venv_python() -> Path:
    """Caminho do interpretador dentro do venv.

    O layout muda conforme o sistema operacional: Windows usa Scripts/ e
    executaveis com extensao .exe; Linux e macOS usam bin/ sem extensao.
    """
    if IS_WINDOWS:
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def running_inside_venv() -> bool:
    """Diz se o interpretador atual e o do venv do projeto.

    Quando um venv esta em uso, sys.prefix aponta para a pasta dele. Fora de um
    venv, sys.prefix e sys.base_prefix sao iguais.
    """
    try:
        return Path(sys.prefix).resolve() == VENV_DIR.resolve()
    except OSError:
        return False


def check_python_version() -> None:
    if sys.version_info < MINIMUM_PYTHON:
        required = ".".join(str(part) for part in MINIMUM_PYTHON)
        current = ".".join(str(part) for part in sys.version_info[:3])
        fail(
            f"Python {required}+ is required, but this is {current}.\n"
            "       On Windows try:  py -3.12 dev.py\n"
            "       On Linux try:    python3.12 dev.py"
        )


def create_venv() -> None:
    step(f"Creating virtual environment at {VENV_DIR.relative_to(BACKEND_DIR.parent)}")

    # Um venv pela metade (interrompido no meio da criacao) causa erros
    # confusos depois. Melhor apagar e comecar limpo.
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)

    subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
    info("done")


def dependencies_are_stale() -> bool:
    """Diz se e preciso (re)instalar as dependencias.

    Compara a data de modificacao dos arquivos de requirements com a do
    marcador gravado na ultima instalacao.
    """
    if not DEPS_STAMP.exists():
        return True

    installed_at = DEPS_STAMP.stat().st_mtime
    return any(
        path.stat().st_mtime > installed_at
        for path in (REQUIREMENTS, REQUIREMENTS_DEV)
        if path.exists()
    )


def install_dependencies() -> None:
    step("Installing dependencies")

    if not REQUIREMENTS_DEV.exists():
        fail(f"{REQUIREMENTS_DEV.name} not found")

    python = str(venv_python())
    subprocess.run([python, "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=True)

    # requirements-dev.txt comeca com "-r requirements.txt", entao esta unica
    # chamada instala as dependencias de execucao e as de desenvolvimento.
    subprocess.run(
        [python, "-m", "pip", "install", "--quiet", "-r", str(REQUIREMENTS_DEV)],
        check=True,
    )

    DEPS_STAMP.write_text("Marcador de instalacao. Nao editar.\n", encoding="utf-8")
    info("done")


def ensure_environment() -> None:
    """Garante que o venv existe e esta com as dependencias em dia."""
    if not venv_python().exists():
        create_venv()
        install_dependencies()
    elif dependencies_are_stale():
        info("requirements changed since last install")
        install_dependencies()


def reexec_inside_venv() -> int:
    """Roda este mesmo script novamente, agora com o Python do venv.

    Usamos subprocess em vez de os.execv porque o comportamento do execv no
    Windows devolve o controle ao terminal antes da hora, o que faria o prompt
    reaparecer com o servidor ainda rodando.
    """
    command = [str(venv_python()), str(Path(__file__).resolve()), *sys.argv[1:]]
    return subprocess.run(command).returncode


# ---------------------------------------------------------------------------
# Tarefas
# ---------------------------------------------------------------------------


def run_tool(arguments: list[str]) -> int:
    """Executa um modulo do venv a partir da pasta backend/.

    Rodar com cwd=BACKEND_DIR e o que faz `import app.main` funcionar sem
    precisar do parametro --app-dir do uvicorn.
    """
    command = [str(venv_python()), "-m", *arguments]
    return subprocess.run(command, cwd=BACKEND_DIR).returncode


def task_dev(extra: list[str]) -> int:
    step("Starting development server")
    info("API      http://127.0.0.1:8000")
    info("Docs     http://127.0.0.1:8000/docs")
    info("Stop     Ctrl+C")
    print(flush=True)
    return run_tool(["uvicorn", "app.main:app", "--reload", *extra])


def task_test(extra: list[str]) -> int:
    step("Running tests")
    return run_tool(["pytest", *extra])


def task_lint(extra: list[str]) -> int:
    step("Running linter")
    return run_tool(["ruff", "check", ".", *extra])


def task_format(extra: list[str]) -> int:
    step("Formatting code")
    return run_tool(["ruff", "format", ".", *extra])


def task_check(extra: list[str]) -> int:
    """Roda tudo que precisa estar verde antes de um commit."""
    return task_lint(extra) or task_test(extra)


def task_install(_extra: list[str]) -> int:
    # O trabalho ja foi feito por ensure_environment(). O underline no nome do
    # parametro sinaliza que ele existe apenas para manter a assinatura comum a
    # todas as tarefas.
    info("environment is ready")
    return 0


TASKS = {
    "dev": task_dev,
    "test": task_test,
    "lint": task_lint,
    "format": task_format,
    "check": task_check,
    "install": task_install,
}


# Texto de ajuda em ingles, seguindo a convencao do projeto: saida de programa
# e para quem usa o projeto (ingles); a docstring acima e explicativa e fica em
# portugues. Sao publicos diferentes, por isso textos diferentes.
USAGE = """ForensicGuard backend task runner.

Usage:
  python dev.py [task] [extra arguments...]

Tasks:
  dev        Start the development server with auto-reload (default)
  test       Run the test suite
  lint       Check the code with ruff
  format     Format the code with ruff
  check      Lint and test - run this before committing
  install    Prepare the virtual environment without running anything

Extra arguments are forwarded to the underlying tool:
  python dev.py dev --port 9000
  python dev.py test -k health

The virtual environment is created and kept up to date automatically.
There is no need to activate it.
"""


def print_usage() -> None:
    print(USAGE, flush=True)


# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------


def main() -> int:
    arguments = sys.argv[1:]

    if arguments and arguments[0] in {"-h", "--help", "help"}:
        print_usage()
        return 0

    # Sem argumento nenhum, o padrao e subir o servidor - igual ao npm run dev.
    task_name = arguments[0] if arguments else "dev"
    extra = arguments[1:]

    if task_name not in TASKS:
        available = ", ".join(TASKS)
        fail(f"unknown task '{task_name}'. Available tasks: {available}")

    check_python_version()
    ensure_environment()

    # Se ainda estamos no Python do sistema, delegamos para o Python do venv.
    if not running_inside_venv():
        return reexec_inside_venv()

    return TASKS[task_name](extra)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        # Ctrl+C e a forma normal de parar o servidor: nao e erro e nao deve
        # despejar um traceback na tela do usuario.
        print()
        raise SystemExit(130) from None
    except subprocess.CalledProcessError as error:
        fail(f"command failed with exit code {error.returncode}")
