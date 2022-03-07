import pytest
import os


def test_examples(testdir):
    """Test the public fixtures."""

    testdir.copy_example("tests/test_examples.py")
    result = testdir.runpytest(
        "-vv",
        "-s",
    )

    # # fnmatch_lines does an assertion internally
    # result.stdout.fnmatch_lines([
    #     '*::test_sth PASSED*',
    # ])

    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_internal_fixtures(testdir):
    """
    Test the private fixtures.
    """
    testdir.copy_example("tests/test_internals.py")
    result = testdir.runpytest(
        "-vv",
        "-s",
    )
    # make sure that we get a '0' exit code for the testsuite
    assert result.ret == 0
