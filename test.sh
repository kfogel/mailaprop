#!/bin/sh

cat test-data/*.mbox                                         \
  | ./mailaprop.py --skip-regexps test-data/skip-regexps.txt \
  > test-data/test-output.eld

if cmp test-data/test-output.eld test-data/expected-output.txt; then
  echo "All tests passed."
  rm test-data/test-output.eld
else
  echo "TESTS FAILED.  SEE DETAILS BELOW." >&2
  echo "" >&2
  diff -u test-data/expected-output.txt test-data/test-output.eld
  echo "" >&2
  echo "TESTS FAILED.  SEE DETAILS ABOVE." >&2
fi
