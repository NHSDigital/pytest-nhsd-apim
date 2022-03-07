from typing import NamedTuple
import sys


class Version(NamedTuple):
    major: int
    minor: int
    micro: int


def parse(version):
    return Version(*[int(x) for x in version.split(".")])


def main(_current, _candidate):

    current = parse(_current)
    candidate = parse(_candidate)

    valid = any(
        [
            (
                # patch incremented by 1
                candidate.major == current.major
                and candidate.minor == current.minor
                and candidate.micro == current.micro + 1
            ),
            (
                # minor incremented by 1, patch reset
                candidate.major == current.major
                and candidate.minor == current.minor + 1
                and candidate.micro == 0
            ),
            (
                # major incremented by minor+patch reset
                candidate.major == current.major + 1
                and candidate.minor == 0
                and candidate.micro == 0
            ),
        ]
    )

    if not valid:
        print(
            f"""
Invalid version {_candidate} in pyproject.toml.

The current version is {_current}.
Please increment the major, minor or patch as appropriate.
"""
        )
        sys.exit(1)


if __name__ == "__main__":
    current = sys.argv[1]
    candidate = sys.argv[2]

    main(current, candidate)
