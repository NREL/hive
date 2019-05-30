#!/usr/bin/env bash

# autotest.sh
# Bash script (Mac-specific) for watching python source
#  for changes and re-running a specific test on save.
# author: tgrushka

runtests() {
  afplay /System/Library/Sounds/Tink.aiff
  
  clear
  { output=$(python -u test_pooling.py|tee /dev/fd/5); } 5>&1
  
  failures=`echo "$output" | grep 'FAILED' | grep -o '[0-9]\+'`
  errors=`echo "$output" | grep 'Error:'`
  if [ -z "$failures" ]
  then
    failed='OK'
  elif [ $failures -eq 1 ]
  then
    failed='failure'
  else
    failed='failures'
  fi

  say "[[volm 0.5]] [[rate 350]] $failures $failed. ... $errors"
}

runtests
while (fswatch -1 ../); do (runtests); done
