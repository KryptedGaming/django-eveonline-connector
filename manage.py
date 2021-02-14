from manager import Manager
import fileinput
import argparse
import subprocess
import os

dir_path = os.path.dirname(os.path.realpath(__file__))
manager = Manager()

example_files = [
    '.travis.yml',
    'setup.py',
    'mkdocs.yml',
    'tox.ini',
    'MANIFEST.in',
    '.coveragerc'
]

get_package_name = subprocess.run(
    ['basename `git rev-parse --show-toplevel`'],
    stdout=subprocess.PIPE,
    shell=True)

get_package_author = subprocess.run(
    ['git config user.name'],
    stdout=subprocess.PIPE,
    shell=True)

get_package_email = subprocess.run(
    ['git config user.email'],
    stdout=subprocess.PIPE,
    shell=True)

get_package_url = subprocess.run(
    ['git remote get-url origin'],
    stdout=subprocess.PIPE,
    shell=True)

package_name = get_package_name.stdout.decode('utf-8').strip()
description = "A Django Application template by Krypted Gaming"
app_name = package_name.replace("-", "_")
title = app_name.title().replace("_", " ")
config_name = ''.join(x for x in app_name.title() if x != '_')
package_author = get_package_author.stdout.decode('utf-8').strip()
package_email = get_package_email.stdout.decode('utf-8').strip()
package_url = get_package_url.stdout.decode('utf-8').strip()


def commands_succeeded(rcs):
    if list(rcs)[0] != 0 or len(set(rcs)) > 1:
        return False
    return True


@manager.command
def echo():
    """Echo package directory."""
    print(dir_path)


@manager.command
def deploy():
    """Deploy package and docs. Type in username and password for PyPi."""
    commands = [
        "python3 setup.py sdist",
        "python3 -m twine upload dist/*",
        "python3 -m mkdocs gh-deploy"
    ]
    command_rcs = set()
    for command in commands:
        print(command)
        command_rcs.add(subprocess.run(
            [command],
            stdout=subprocess.PIPE,
            shell=True).returncode)


@manager.command
def venv():
    """Create a virtual environment."""
    command_rc = subprocess.run(
        [f"python3 -m venv {dir_path}/venv"],
        stdout=subprocess.PIPE,
        shell=True).returncode
    if command_rc != 0:
        print(
            f"Failed to create virtual env: RC={command_rc}")
        exit()


@ manager.command
def init():
    """Initialize the project."""
    # Create application
    create_project = subprocess.run(
        [f"django-admin startapp {app_name}"],
        stdout=subprocess.PIPE,
        shell=True)

    if create_project.returncode != 0 and create_project.returncode != 1:
        print(
            f"Failed to create Django application: RC={create_project.returncode}")
        exit()

    # Create files
    example_file_creation_rcs = set()

    for example_file in example_files:
        command = f'cp {dir_path}/{example_file}.example {dir_path}/{example_file}'
        print(command)
        example_file_creation_rcs.add(subprocess.run(
            [command],
            stdout=subprocess.PIPE,
            shell=True
        ).returncode)

    if not commands_succeeded(example_file_creation_rcs):
        print("Failed to create necessary files.")
        exit()

    # Modify Files
    for example_file in example_files:
        lines_replaced = 0
        with fileinput.FileInput(f"{dir_path}/{example_file}", inplace=True) as file:
            for line in file:
                if 'django_package_template' in line:
                    lines_replaced += 1
                print(line.replace('django_package_template', app_name), end='')
        print(
            f"Updating file: {dir_path}/{example_file} ... {lines_replaced} lines replaced")

    # Create __init__.py
    init_py = (
        f"__title__ = '{title}'" + "\n"
        f"__description__ = '{description}'" + "\n"
        f"__package_name__ = '{package_name}'" + "\n"
        f"__github_url__ = '{package_url}'" + "\n"
        f"__version__ = '0.0.1'" + "\n"
        f"__author__ = '{package_author}'" + "\n"
        f"__author_email__ = '{package_email}'" + "\n"
        f"__license__ = 'MIT License'" + "\n"
        f"__copyright__ = f\"Copyright © 2017-2020 {package_author}. All rights reserved.\"" + "\n"
        f"default_app_config = \"{app_name}.apps.{config_name}Config\"" + "\n"
    )
    f = open(f"{app_name}/__init__.py", "a+")
    f.write(init_py)

    print("Successfully initialized project")


@ manager.command 
def prune():
    """Prune all .example files. WARNING: Init will no longer function."""
    for example_files in example_files:
        command_rcs = set()
        command = f'rm -rf {dir_path}/{example_file}.example'
        print(command)

        command_rcs.add(subprocess.run(
            [command],
            stdout=subprocess.PIPE,
            shell=True
        ).returncode)
        if not commands_succeeded(command_rcs):
            print("Failed to clear files")
            exit()

@ manager.command
def purge():
    """Purge all created files."""
    for example_file in example_files:
        command_rcs = set()
        command = f'rm -rf {dir_path}/{example_file}'
        print(command)

        command_rcs.add(subprocess.run(
            [command],
            stdout=subprocess.PIPE,
            shell=True
        ).returncode)
        if not commands_succeeded(command_rcs):
            print("Failed to clear files")
            exit()

    command = f'rm -rf {dir_path}/{app_name}'
    print(command)
    command_rcs.add(subprocess.run(
        [command],
        stdout=subprocess.PIPE,
        shell=True
    ).returncode)
    if not commands_succeeded(command_rcs):
        print("Failed to clear files")
        exit()

    extra_files = [
        'coverage.xml',
        'dist',
        '.coverage',
        '*.egg-info',
        'site',
        '.tox',
        'venv'
    ]
    
    for example_file in extra_files:
        command_rcs = set()
        command = f'rm -rf {dir_path}/{example_file}'
        print(command)

        command_rcs.add(subprocess.run(
            [command],
            stdout=subprocess.PIPE,
            shell=True
        ).returncode)
        if not commands_succeeded(command_rcs):
            print("Failed to clear files")
            exit()


if __name__ == '__main__':
    manager.main()
