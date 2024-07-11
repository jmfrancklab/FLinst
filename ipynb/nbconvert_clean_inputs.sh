#!/bin/bash
b=`basename $1 .ipynb`
jupyter nbconvert --to python $b.ipynb
sed -i 's/^\(# \)In\[.*/\1/' $b.py
