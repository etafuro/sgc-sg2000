# This script requires fpm installed in your Linux Python env

pyinstaller --onefile sg2000_ux_1.py
fpm -s dir -t deb -n sg2000_ux -v 1.0 ./dist/sg2000_ux_1.exe