#!/usr/bin/env bash
# Script to compile asyncpg, uvloop and Pillow
python_version=$(python3 -V)
if [[ $python_version != "Python 3.8"* ]];
then
    echo "You need python3 to be a 3.8 version. Use a virtualenv."
fi
mkdir build
cd build
python3 -m pip install -U git+https://github.com/cython/cython
git clone https://github.com/MagicStack/uvloop
cd uvloop
git submodule init
git submodule update
make
python3 setup.py install
cd ..
git clone https://github.com/MagicStack/asyncpg
cd asyncpg
git submodule init
git submodule update
python3 setup.py install
cd ..
git clone https://github.com/python-pillow/Pillow
cd Pillow
make install
cd ..
cd ..
rm -rf build
echo "--------------------------"
echo "    Install successful"
echo "--------------------------"

