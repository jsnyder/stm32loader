"""Run unit tests in a fresh virtualenv using nox."""

from shutil import rmtree

import nox


@nox.session(python=["2.7", "3.4", "3.5", "3.6", "3.7"])
def tests(session):
    """
    Install stm32loader package and execute unit tests.

    Use chdir to move off of the current folder, so that
    'import stm32loader' imports the *installed* package, not
    the local one from the repo.
    """
    # setuptools does not like multiple .whl packages being present
    # see https://github.com/pypa/setuptools/issues/1671
    rmtree("./dist", ignore_errors=True)
    session.install(".")
    session.install("pytest")
    if session.python == "2.7":
        session.install("mock")
    session.chdir("tests")
    session.run("pytest", "./")


@nox.session(python=["3.6"])
def lint(session):
    """
    Run code verification tools flake8, pylint and black.

    Do this in order of expected failures for performance reasons.
    """
    session.install("black")
    session.run("black", "--check", "stm32loader")

    session.install("pylint")
    # pyserial for avoiding a complaint by pylint
    session.install("pyserial")
    session.run("pylint", "stm32loader")

    session.install("flake8", "flake8-isort")
    # not sure why this needs an explicit --config
    session.run("flake8", "stm32loader", "--config=setup.cfg")
