import shutil
from pathlib import Path

# third party
import click
from sigal import build

from utils import (
    azure_backup_container,
    azure_create_container,
    azure_delete_dir,
    azure_get_containers,
    azure_upload_dir,
    do_delete_dir,
    do_download_file,
    do_upload_dir,
    do_upload_file,
    unzip_file,
    zipdir,
)


@click.group()
@click.pass_context
def cli(ctx):
    """Helper commands for managing the website and backend data.

    They are used both in the continuous integration pipeline as well as manually from time to time.
    """
    ctx.ensure_object(dict)


@cli.command()
@click.option(
    "--local",
    "-l",
    default="albums.zip",
    show_default=True,
    help="Local filename to save.",
)
@click.option(
    "--remote",
    "-r",
    default="albums.zip",
    show_default=True,
    help="Remote filename to download.",
)
@click.option(
    "--force",
    "-f",
    default=False,
    show_default=True,
    is_flag=True,
    help="Force the download or not.",
)
def do_download(local, remote, force):
    """Download and unzip albums.zip from Digital Ocean."""
    do_download_file(remote_file=remote, local_file=local, force=force)
    unzip_file(local)


@cli.command()
@click.option(
    "--file",
    "-f",
    default="albums.zip",
    show_default=True,
    help="Filename of album archive.",
)
def do_backup(file):
    """Backup albums to Digital Ocean Spaces.

    I run this command locally on the machine where I use GIMP to create new files to put into the albums.
    It zips up the albums/ directory and uploads it to (currently) Digital Ocean Spaces.
    """
    # upload_location is going to be top level of the DO Space/Azure container at the moment
    upload_location = file
    Path(file).unlink(missing_ok=True)
    zipdir("albums/", file)
    # this will overwrite what is in Digital Ocean!
    do_upload_file(file, upload_location)


@cli.command()
@click.option(
    "--container",
    "-c",
    default="$web",
    show_default=True,
    help="Azure Blob Storage container.",
)
@click.option(
    "--dir",
    "-d",
    "dir_",
    default="_build",
    show_default=True,
    help="Local directory to deploy to Azure.",
)
@click.option(
    "--fresh-start",
    "-f",
    default=False,
    show_default=True,
    is_flag=True,
    help="Delete Azure Storage container contents first.",
)
@click.pass_context
def azure_deploy(ctx, container, dir_, fresh_start):
    """Deploy built static files to Azure.

    This command simulates a Travis CI deployment which uploads the _build directory to Azure Blob Storage.
    It is useful for local development without doing a git commit/push.
    """

    # destination = "travis-builds"
    # do_upload_dir(dir_, destination)

    if fresh_start:
        ctx.invoke(azure_clear, container=container, prefix="")
    azure_upload_dir(dir_, container)
    # azure_upload_dir("albums", "stains")


@cli.command()
@click.option(
    "--container",
    "-c",
    default="$web",
    show_default=True,
    help="Azure Blob Storage container.",
)
@click.option(
    "--prefix",
    "-p",
    default="",
    help="Delete all storage blobs with this prefix. If not provided, deletes all files in the container.",
)
def azure_clear(container, prefix):
    """Delete directory from Azure Storage."""
    # destination = "travis-builds/"
    # do_delete_dir(destination)

    azure_delete_dir(container, prefix)


@cli.command()
@click.option(
    "--source-container",
    "-s",
    default="$web",
    show_default=True,
    help="Azure production web container.",
)
@click.option(
    "--backup-container",
    "-b",
    default="backup",
    show_default=True,
    help="Azure backup container.",
)
@click.pass_context
def azure_backup_website(ctx, source_container, backup_container):
    """Backup website on Azure Storage."""
    containers = azure_get_containers(prefix=backup_container)
    container_names = [container["name"] for container in containers]

    # either create a fresh backup container, or clear out the old one
    if backup_container not in container_names:
        print(f"Backup container '{backup_container}' not found. Creating.")
        azure_create_container(backup_container)
    else:
        ctx.invoke(azure_clear, container=backup_container, prefix="")

    azure_backup_container(
        src_container=source_container, dest_container=backup_container
    )


@click.option(
    "--dir",
    "-d",
    "dir_",
    default="_build",
    show_default=True,
    help="Local directory to delete.",
)
@cli.command()
def sigal_clean(dir_):
    """Clean the local sigal build directory."""
    shutil.rmtree(dir_, ignore_errors=True)


@cli.command()
@click.pass_context
def sigal_build(ctx):
    """Build the website using Sigal."""
    ctx.invoke(sigal_clean)
    ctx.invoke(build)


@cli.command()
@click.pass_context
def sigal_compress(ctx):
    """Compress images using Sigal."""
    destination = "_compressed_images"
    ctx.invoke(sigal_clean, dir_=destination)
    ctx.invoke(build, config="sigal.conf.img.py", destination=destination)


if __name__ == "__main__":
    cli()
