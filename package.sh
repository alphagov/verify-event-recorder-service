#!/usr/bin/env bash
set -eu

if [ -f tmp/ ];
then
    rm -r tmp/
fi

if [ -f package.zip ];
then
    rm -f package.zip
fi

virtualenv --python=python3 package-env
package-env/bin/pip install -r requirements/prod.txt

mkdir -p tmp/src/
cp -r package-env/lib/python3.6/site-packages/ tmp/
cp -r src/ tmp/src/

cd tmp
zip -qr package.zip .
mv package.zip ../
cd ..

rm -r tmp/