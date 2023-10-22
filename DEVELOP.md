
# How to contribute


## Installation

Checkout the latest master.

    git clone https://github.com/florisla/stm32loader.git
    
Install in editable mode with development tools (preferable in a virtual
environment).

    python -m venv .venv
    .\.venv\bin\activate
    pip uninstall stm32loader
    pip install --editable .[dev]
    
    
## Testing

Run pytest.

    pytest .
    
    
## Linting

Run flake8, pylint and black.

    flake8 stm32loader
    pylint stm32loader
    black --check stm32loader 
    
    
## Commit messages

I try to follow the 'conventional commits' commit message style;
see https://www.conventionalcommits.org/ .
    
    
## Bump the version number

    bumpversion --new-version 1.0.8-dev bogus-part
    
    
## Tag a release

First, bump the version number to a release version.
Then create the git tag.

    git tag -a "v1.0.9" -m "release: Tag version v1.0.9"
    
Also push it to upstream.

    git push origin v1.0.9
