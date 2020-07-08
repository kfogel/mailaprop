#!/bin/sh

# This is not a real test suite yet, but it's a first step.
# You have to just read the output and see if it looks right.

cat test-data/*.mbox                                         \
  | ./mailaprop.py --skip-regexps test-data/skip-regexps.txt \
  > test-output.eld

cat test-output.eld
