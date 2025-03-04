from importlib.metadata import version
import click
from git import Repo
from git.exc import GitError, GitCommandError
from pathlib import Path
import re
from typing import List, Union
import tempfile
from rich.console import Console


def parse_csv_option(ctx, param, value):
    """
    Callback function to parse list from csv
    """
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(',') if item.strip())


def is_valid_github_url(url: str) -> bool:
    """
    Validate if the provided URL is a valid GitHub repository URL.
    Args:
        url (str): GitHub URL to validate
    Returns:
        bool: True if valid, False otherwise
    """
    github_pattern = r'^https?://github\.com/[\w-]+/[\w.-]+(?:\.git)?$'
    return bool(re.match(github_pattern, url))


def get_repository_error_message(error_output: str) -> str:
    """
    Determine if repository is private or doesn't exist based on git error message.
    Args:
        error_output (str): Git error message
    Returns:
        str: User-friendly error message
    """
    if (
        'Authentication failed' in error_output
        or 'could not read Username' in error_output
    ):
        return 'Repository is private. Please check the URL or your access permissions.'
    elif (
        'not found' in error_output.lower()
        or 'repository not found' in error_output.lower()
    ):
        return 'Repository does not exist. Please check the URL.'
    else:
        return 'Repository is either private or does not exist.'


def clone_repository(url: str, temp_dir: str) -> Path:
    """
    Clone a GitHub repository into a temporary directory.
    Args:
        url (str): GitHub repository URL
        temp_dir (str): Path to temporary directory
    Returns:
        Path: Path to the cloned repository
    Raises:
        GitCommandError: If cloning fails
        ValueError: If URL is invalid
    """
    if not is_valid_github_url(url):
        raise ValueError(
            'Invalid GitHub URL format. Expected format: https://github.com/username/repository'
        )

    repo_path = Path(temp_dir) / url.split('/')[-1].replace('.git', '')

    try:
        Repo.clone_from(url, repo_path)
        return repo_path
    except GitCommandError as e:
        error_message = get_repository_error_message(str(e))
        raise GitError(error_message)


def analyze_sources(
    root_path: Path,
    include_dirs: tuple[str, ...] = (),
    exclude_dirs: tuple[str, ...] = (),
    blacklist: tuple[str, ...] = (),
    extensions: tuple[str, ...] = (),
    is_all: bool = False,
) -> Union[dict[Path, List[Path]], List[Path]]:
    """
    analyze directory structure using rglob because we're too fancy for os.walk
    returns a dictionary of folder paths and their source files

    @param root_path: the path to your markdown wasteland
    @return: a dict of folders and their files, organized like your life isn't
    """
    file_groups: dict[Path, List[Path]] = {}

    for file_path in root_path.rglob('*'):
        # skip directories we hate
        if any(ignore_dir in file_path.parts for ignore_dir in exclude_dirs):
            continue

        # include directories we love
        if include_dirs and not any(
            re.search(f'(^|/){re.escape(inc_dir)}(/|$)', str(file_path))
            for inc_dir in include_dirs
        ):
            continue

        if (
            file_path.is_file()
            and file_path.suffix in extensions
            and file_path.name.lower() not in blacklist
        ):
            dir_path = file_path.parent

            # initialize the list for this directory if it's new
            if dir_path not in file_groups:
                file_groups[dir_path] = []

            # add the file to its directory group
            file_groups[dir_path].append(file_path)

    if is_all:
        return [file for files in file_groups.values() for file in files]

    return file_groups


def concatenate_sources(
    file_groups: Union[dict[Path, List[Path]], List[Path]],
    root_path: Path,
    output_dir: Path,
    is_all: bool,
):
    """
    Concatenates files and export them to an output_dir
    """

    Path(Path(output_dir) / root_path.name).mkdir(parents=True, exist_ok=True)

    if isinstance(file_groups, dict):
        total_folders = len(file_groups)
        total_files = sum(len(files) for files in file_groups.values())

        click.secho(
            f'\n🚀 Found {total_files} files and {total_folders} folders to merge.',
            fg='blue',
        )
    else:
        total_files = len(file_groups)

        click.secho(
            f'\n🚀 Found {total_files} files and to merge into a `single source file`.',
            fg='blue',
        )

    if is_all and isinstance(file_groups, list):
        output_content = []
        output_content.append(f"""
{'#' * 50}
# Repository: {root_path.name}
# Total files merged: {total_files}
{'#' * 50}\n
""")

        # Ensure files are a list
        files_to_process = (
            file_groups
            if isinstance(file_groups, list)
            else list(file_groups.values())[0]
        )

        for idx, file_path in enumerate(files_to_process, 1):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                    output_content.append(f"""
\n{'=' * 80}
Source File {idx}: {file_path.relative_to(root_path)}
{'=' * 80}\n
{content}
""")

            except Exception as e:
                click.secho(
                    f'\n❌ Failed to process {file_path.relative_to(root_path)} - Error: {str(e)}',
                    fg='red',
                )
                continue

        # Write to a single file
        output_file = Path(output_dir) / root_path.name / f'{root_path.name}.txt'
        output_file.write_text('\n'.join(output_content), encoding='utf-8')
    if not is_all and isinstance(file_groups, dict):
        i = 1
        with click.progressbar(
            file_groups.items(),
            length=len(file_groups),
            label=click.style('📁 Processing folders', fg='green'),
            fill_char=click.style('█', fg='green'),
            empty_char='░',
        ) as bar:
            for dir_path, file_list in file_groups.items():
                folder_name = Path(dir_path).name
                output_content = []

                output_content.append(f"""
{'#' * 50}
# Folder: {dir_path.relative_to(root_path)}
# Number of files merged: {len(file_list)}
{'#' * 50}\n
""")

                for idx, file_path in enumerate(file_list, 1):
                    try:
                        full_path = Path(root_path) / file_path
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                            output_content.append(f"""
\n{'=' * 80}
Source File {idx}: {file_path.relative_to(root_path)}
{'=' * 80}\n
{content}
""")

                    except Exception as e:
                        click.secho(
                            f'\n❌ Failed to process {Path(file_path).relative_to(root_path)} - Error: {str(e)}',
                            fg='red',
                        )

                    continue

                output_file = (
                    Path(output_dir) / root_path.name / f'{i}_{folder_name}.txt'
                )
                output_file.write_text('\n'.join(output_content), encoding='utf-8')

                i += 1
                bar.update(1)


@click.command()
@click.argument('repo-url', type=click.STRING)
@click.version_option(version=version('sewsource'), prog_name='sewsource')
@click.option(
    '-a',
    '--all',
    is_flag=True,
    show_default=True,
    default=False,
    help='Embed all the source into a single text',
)
@click.option(
    '-o',
    '--output-dir',
    default=Path.home() / '.sewsource',
    show_default=True,
    help='Output directory to save the sewed source',
)
@click.option(
    '-i',
    '--include-dirs',
    callback=parse_csv_option,
    help='Only include directories that should be included as sources (comma-separated)',
)
@click.option(
    '-x',
    '--exclude-dirs',
    default='.git,.github',
    callback=parse_csv_option,
    show_default=True,
    help='Exclude directories that should not be included as sources (comma-separated)',
)
@click.option(
    '-b',
    '--blacklist',
    callback=parse_csv_option,
    help='Blacklist filenames that should not be included as sources (comma-separated)',
)
@click.option(
    '-e',
    '--extensions',
    default='.md,.mdx',
    callback=parse_csv_option,
    show_default=True,
    help='Extensions that should be whitelisted as source (comma-separated)',
)
def main(
    repo_url: str,
    all: bool,
    output_dir: Path,
    include_dirs: tuple[str, ...],
    exclude_dirs: tuple[str, ...],
    blacklist: tuple[str, ...],
    extensions: tuple[str, ...],
):
    """
    CLI tool to clone a GitHub repository into a temporary directory.
    """

    console = Console()
    repo_path: Path

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            with console.status(f'Cloning Repo: {repo_url}', spinner='circle'):
                repo_path = clone_repository(repo_url, temp_dir)
            click.secho(f'✅Successfully cloned repository to: {repo_path}', fg='green')
        except (GitError, ValueError) as e:
            click.echo(f'❌Error: {str(e)}')
            return 1

        try:
            click.secho('\n⌛Analyzing...', fg='blue')

            file_groups = analyze_sources(
                repo_path, include_dirs, exclude_dirs, blacklist, extensions, is_all=all
            )

            concatenate_sources(file_groups, repo_path, output_dir, is_all=all)
        except Exception as e:
            click.echo(f'❌Error: {str(e)}')

    click.secho(
        f'\n✨ Done! Your source soup is served at `{Path(output_dir) / repo_path.name}`!',
        fg='green',
        bold=True,
    )


if __name__ == '__main__':
    main()
