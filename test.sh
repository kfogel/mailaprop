#!/bin/sh

cat test-data/* | ./mailaprop.py > test-output.eld
cat test-output.eld
