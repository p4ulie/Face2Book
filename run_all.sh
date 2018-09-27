#!/usr/bin/env bash

for YEAR in `seq 2008 2018`;
do
  python face2book.py -y "${YEAR}" > "book_${YEAR}.html"
  echo "${YEAR}"
done

