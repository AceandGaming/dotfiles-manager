import typer

from app.file import initialise
from app.var import DOTFILES_PATH

app = typer.Typer(add_completion=False)


@app.command("getpath")
def c_get_path():
    typer.echo(DOTFILES_PATH.absolute())


@app.command("update")
def c_update():
    typer.echo("updating")


@app.command("init")
def c_init():
    initialise()


def main():
    app()
