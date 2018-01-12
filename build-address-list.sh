#!/bin/sh

### This example script shows how to drive mailaprop.py to produce a
### file of email addresses in the format that mailaprop.el expects.

# EDIT HERE: Tell the script where to find mailaprop.py.
MAILAPROP=mailaprop.py

# EDIT HERE: Say where your file of email addresses will live.
OUTFILE=${HOME}/private/mailaprop/mailaprop-addresses.eld
TMP=${OUTFILE}.tmp

# Clear out the tempfile.
> ${TMP}

# EDIT HERE: Pipe *all* your email through one invocation of mailaprop.py.
cat test-data/*.mbox | ${MAILAPROP} >> ${TMP}
# Your email may be spread across many mbox files, and a given mbox
# file may contain one or more email messages.  Here's another example
# command line, designed for an nnmail tree containing thousands of
# mbox files each holding a single message:
#
# find ${HOME}/mail -type f -regex ".*/[0-9]+$" -print | ${MAILAPROP} >> ${TMP}

mv ${TMP} ${OUTFILE}

echo "Mailaprop address database created: '${OUTFILE}'"
