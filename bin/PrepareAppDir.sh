#!/bin/sh
#
# Used to prepare the AppDir bundle directory. -*- mode: sh -*-
#
# Written by Tristan Van Berkom <tristan@upstairslabs.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

APP_DIR_ROOT=$1
BUNDLE_DIR=$2

if test -z ${APP_DIR_ROOT} || test -z ${BUNDLE_DIR}; then
    echo "Usage ./PrepareAppDir.sh /path/to/AppImage/Install /path/to/glade/build/linux"
    exit 0;
fi

cp -R /usr/share/themes/* ${APP_DIR_ROOT}/share/themes

echo -n "Removing various unwanted files from the image... "
# Remove static libraries and libtool archives
rm -f `find ${APP_DIR_ROOT} -name "*.a"`
rm -f `find ${APP_DIR_ROOT} -name "*.la"`
rm -f `find ${APP_DIR_ROOT} -name "*.pyc"`
rm -f `find ${APP_DIR_ROOT} -name "*.pyo"`

# Remove include directory
#rm -rf ${APP_DIR_ROOT}/include

# Remove various stuff in /share
#rm -rf ${APP_DIR_ROOT}/share/man
#rm -rf ${APP_DIR_ROOT}/share/info
#rm -rf ${APP_DIR_ROOT}/share/help
#rm -rf ${APP_DIR_ROOT}/share/doc
#rm -rf ${APP_DIR_ROOT}/share/gtk-doc
#rm -rf ${APP_DIR_ROOT}/share/gdb
#rm -rf ${APP_DIR_ROOT}/share/gdm
#rm -rf ${APP_DIR_ROOT}/share/vala
#rm -rf ${APP_DIR_ROOT}/share/pkgconfig
#rm -rf ${APP_DIR_ROOT}/share/gnome
#rm -rf ${APP_DIR_ROOT}/share/xml
#rm -rf ${APP_DIR_ROOT}/share/bash-completion
#rm -rf ${APP_DIR_ROOT}/share/appdata
#rm -rf ${APP_DIR_ROOT}/share/dbus-1
#rm -rf ${APP_DIR_ROOT}/share/glib-2.0/codegen
#rm -rf ${APP_DIR_ROOT}/share/glib-2.0/gdb
#rm -rf ${APP_DIR_ROOT}/share/glib-2.0/gettext

echo -n "Removing encoded rpath from all binaries... "
chrpath -d `find ${APP_DIR_ROOT} -name "*.so"`
echo "Done."

echo -n "Setting up symlinks for new environment... "
WORK_DIR=`pwd`

# Create a /usr link in the install prefix, this is for AppImageKit to find the desktop icon properly
cd ${APP_DIR_ROOT}
ln -s . usr

# Create a symlink at ${APP_DIR_ROOT}${APP_DIR_ROOT} which
# links back to the root of the bundle.
#
# All our paths are relative to the jhbuild prefix, so we need
# this symlink to pretend that the build prefix is the root.
mkdir -p ${APP_DIR_ROOT}/${APP_DIR_ROOT%linux_x86_64}
cd ${APP_DIR_ROOT}/${APP_DIR_ROOT%linux_x86_64}
ln -s ../../.. linux_x86_64

# Restore working directory
cd $WORK_DIR
echo "Done."

echo -n "Fixing bin/pitivi to usable in the embeded env ... "
cat ${APP_DIR_ROOT}/bin/pitivi |sed -e "s|'${APP_DIR_ROOT}|os.path.join(os.environ['APPDIR'], 'usr/') + '|g" > /tmp/pitivi
mv /tmp/pitivi  ${APP_DIR_ROOT}/bin/
chmod +x ${APP_DIR_ROOT}/bin/pitivi

cat ${APP_DIR_ROOT}lib/pitivi/python/pitivi/configure.py |sed -e "s|'${APP_DIR_ROOT}|os.path.join(os.environ['APPDIR'], 'usr/') + '|g" > /tmp/configure.py
mv /tmp/configure.py  ${APP_DIR_ROOT}/lib/pitivi/python/pitivi/configure.py
echo "Done."

echo -n "Fixing libbz2.so symlink to be relative... "
cd ${APP_DIR_ROOT}/lib
rm libbz2.so libbz2.so.1.0
ln -s libbz2.so.1.0.6 libbz2.so 
ln -s libbz2.so.1.0.6 libbz2.so.1.0
echo "Done."


echo -n "Installing desktop file and runner script... "
cp ${APP_DIR_ROOT}/share/applications/pitivi.desktop ${APP_DIR_ROOT}
cat ${BUNDLE_DIR}/AppRun | sed -e "s|@APP_DIR_ROOT@|${APP_DIR_ROOT}|g" > ${APP_DIR_ROOT}/AppRun
chmod +x ${APP_DIR_ROOT}/AppRun
echo "Done."

echo -n "Fixing pixbuf loaders to have bundle relative paths... "
# Post process the loaders.cache file to use relative paths, we use a for loop here
# just because we're not sure the exact location, it could be in lib or lib64
for cache in `find ${APP_DIR_ROOT} -path "*gdk-pixbuf-2.0/2.10.0/loaders.cache"`; do
    cat $cache | sed -e "s|${APP_DIR_ROOT}|\./|g" > $cache.1 && mv $cache.1 $cache;
done
echo "Done."

rm ~/pitivi-$(date +"%m_%d_%Y")
AppImageAssistant ${APP_DIR_ROOT} ~/pitivi-$(date +"%m_%d_%Y")
