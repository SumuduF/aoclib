import argparse
import sys
from itertools import groupby
from inspect import signature

def run_solution(solution):
    """Basic AoC main: takes care of getting input and printing the answer."""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--part", "-p", type=int)
    arg_parser.add_argument("filename", nargs="?")
    args = arg_parser.parse_args()

    if args.filename is not None:
        input_lines = _read_rstripped_lines(open(args.filename, "r"))
    else:
        input_lines = _read_rstripped_lines(sys.stdin)

    if len(signature(solution).parameters) > 1:
        answer = solution(input_lines, args.part)
    else:
        if args.part is not None:
            sys.stderr.write(f"WARNING: ignoring --part={args.part}\n")
        answer = solution(input_lines)

    print(answer)

def _read_rstripped_lines(infile):
    """Returns lines (rstripped) from the given file (closes the file)."""
    with infile as f:
        return [line.rstrip() for line in f]

# split lines into groups separated by blank lines
def line_groups(lines):
    for is_group, g in groupby(lines, bool):
        if not is_group: continue
        yield list(g)

# python3 killed cmp for some reason
def cmp(a, b):
    return (a > b) - (a < b)

# handy for normalizing range endpoint order
def minmax(a, b):
    return (min(a, b), max(a, b))
