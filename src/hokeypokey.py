import click
import pokeit
import checkit
import settings
import sys


@click.command()
@click.option('-uq', help='unique part of @id uri')
@click.option('-s', help='success criteria file')
@click.argument('template', type=click.File('rb'))
def main(uq, s, template):
    """Simple DLCS pipeline tester"""

    exit_code, manifest = pokeit.pokeit(uq, s, template)
    if exit_code == 0:
        manifest = settings.PRESLEY_BASE + f"/customer/manifest?manifest_id={manifest}"
        exit_code = checkit.checkit(manifest)
    sys.exit(exit_code)


if __name__ == '__main__':

    main()
