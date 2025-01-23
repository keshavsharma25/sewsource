import click
from git import Repo
from git.exc import GitError, GitCommandError
from pathlib import Path
import re
from typing import List
import tempfile
from rich.console import Console


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
) -> dict[Path, List[Path]]:
    """
    analyze directory structure using rglob because we're too fancy for os.walk
    returns a dictionary of folder paths and their source files

    @param root_path: the path to your markdown wasteland
    @return: a dict of folders and their files, organized like your life isn't
    """
    file_groups: dict[Path, List[Path]] = {}

    # rglob through all files like we're searching for meaning in life
    for file_path in root_path.rglob('*'):
        # skip directories we hate
        if any(ignore_dir in file_path.parts for ignore_dir in exclude_dirs):
            continue

        if include_dirs and not any(
            inc_dir in str(file_path) for inc_dir in include_dirs
        ):
            continue

        # check if it's a file and matches our extension fetish
        if (
            file_path.is_file()
            and file_path.suffix in extensions
            and file_path.name.lower() not in blacklist
        ):
            # get the parent directory path
            dir_path = file_path.parent

            # initialize the list for this directory if it's new
            if dir_path not in file_groups:
                file_groups[dir_path] = []

            # add the file to its directory group
            file_groups[dir_path].append(file_path)

    return file_groups


def concatenate_sources(
    file_groups: dict[Path, List[Path]], root_path: Path, output_dir: Path
):
    """
    Concatenates files and export them to an output_dir
    """
    Path(Path(output_dir) / root_path.name).mkdir(parents=True, exist_ok=True)
    total_folders = len(file_groups)
    total_files = sum(len(files) for files in file_groups.values())

    click.secho(
        f'\n🚀 Found {total_files} files and {total_folders} folders to merge.',
        fg='blue',
    )

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

            output_file = Path(output_dir) / root_path.name / f'{i}_{folder_name}.txt'
            output_file.write_text('\n'.join(output_content), encoding='utf-8')

            i += 1
            bar.update(1)


@click.command()
@click.option('-r', '--repo-url', required=True, help='GitHub repository URL to clone')
@click.option(
    '-o',
    '--output-dir',
    default=Path.home() / '.sew_source',
    show_default=True,
    help='Output directory to save the sewed source',
)
@click.option(
    '-i',
    '--include-dirs',
    multiple=True,
    help='Only include directories that should be included as sources',
)
@click.option(
    '-x',
    '--exclude-dirs',
    multiple=True,
    help='Exclude directories that should not be included as sources',
)
@click.option(
    '-b',
    '--blacklist',
    multiple=True,
    help='Blacklist filenames that should not be included as sources',
)
@click.option(
    '-e',
    '--extensions',
    default=['.md', '.mdx'],
    show_default=True,
    help='Extensions that should be whitelisted as source',
)
def main(
    repo_url: str,
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

    with tempfile.TemporaryDirectory() as temp_dir:
        click.secho(f'📁 Created temporary directory: {temp_dir}\n')
        repo_path: Path

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
                repo_path, include_dirs, exclude_dirs, blacklist, extensions
            )

            concatenate_sources(file_groups, repo_path, output_dir)
        except Exception as e:
            click.echo(f'❌Error: {str(e)}')

    click.secho('\n✨ Done! Your markdown soup is served!', fg='green', bold=True)


if __name__ == '__main__':
    main()
