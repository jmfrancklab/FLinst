#!/usr/bin/bash
# 
# Assuming that users have their own directories, and they want to pull up to
# date scripts into those directories, we can use this
git commit -a -m "about to start"
orig_dir="$(pwd)"
cd /c/apps-su/FLinst
echo "I'm in this branch of FLinst:\n$(git branch)"
echo "is it clean?:\n$(git status -s)"
git pull
cp examples/gds_for_tune.py $orig_dir
cp examples/collect_SC.py $orig_dir
cp examples/run_generic_echo.py $orig_dir
cp examples/run_nutation.py $orig_dir
cp examples/run_field_dep_justMW.py $orig_dir

cd /c/git/pyspecdata
echo "I'm in this branch of pyspecdata:\n$(git branch)"
echo "is it clean?:\n$(git status -s)"

cd /c/git/proc_scripts
echo "I'm in this branch of proc_scripts:\n$(git branch)"
echo "is it clean?:\n$(git status -s)"
git pull
cp examples/generate_SC_PSD.py $orig_dir
cp examples/proc_raw.py $orig_dir
cp examples/proc_nutation.py $orig_dir
cp examples/proc_fieldSweep.py $orig_dir


