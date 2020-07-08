#!/bin/sh

cat test-data/*.mbox                                         \
  | ./mailaprop.py --skip-regexps test-data/skip-regexps.txt \
  > test-data/test-output.eld

if ! [ -s test-data/test-output.eld ]; then
  echo "TESTS FAILED BECAUSE NO OUTPUT PRODUCED." >&2
  rm -f test-data/test-output.eld
  exit 1
elif cmp test-data/test-output.eld test-data/expected-output.txt; then
  echo "All tests passed."
  rm -f test-data/test-output.eld
  exit 0
else
  echo "TESTS FAILED.  SEE DETAILS BELOW." >&2
  echo "" >&2
  diff -u test-data/expected-output.txt test-data/test-output.eld
  echo "" >&2
  echo "TESTS FAILED.  SEE DETAILS ABOVE." >&2
  exit 1
fi
