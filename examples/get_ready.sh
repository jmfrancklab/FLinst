#!/usr/bin/bash
# 
# Assuming that users have their own directories, and they want to pull up to
# date scripts into those directories, we can use this
echo "The following refers to the git for this directory (hopefully the user_exp)"
echo "==========================================================================="
git -c core.safecrlf=false commit -a -m "save files from last time"
orig_dir="$(pwd)"
echo "==========================================================================="
cd /c/apps-su/FLinst
echo -e "I'm in this branch of FLinst:\n$(git rev-parse --abbrev-ref @)"
echo -e "is it clean?:\n$(git status -s)"
git pull
cp examples/gds_for_tune.py $orig_dir
cp examples/collect_SC.py $orig_dir
cp examples/run_generic_echo.py $orig_dir
cp examples/run_nutation.py $orig_dir
cp examples/run_field_dep_justMW.py $orig_dir
echo "==========================================================================="
cd /c/git/pyspecdata
echo -e "I'm in this branch of pyspecdata:\n$(git rev-parse --abbrev-ref @)"
echo -e "is it clean?:\n$(git status -s)"
git pull
echo "==========================================================================="
cd /c/git/proc_scripts
echo -e "I'm in this branch of proc_scripts:\n$(git rev-parse --abbrev-ref @)"
echo -e "is it clean?:\n$(git status -s)"
git pull
cp examples/generate_SC_PSD.py $orig_dir
cp examples/proc_raw.py $orig_dir
cp examples/proc_nutation.py $orig_dir
cp examples/proc_fieldSweep.py $orig_dir
cd $orig_dir
git -c core.safecrlf=false commit -a -m "updated all scripts"
