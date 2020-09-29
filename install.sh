mkdir -p /opt/eveonline/static/
cp /sqlite-latest.sqlite.bz2 /opt/eveonline/static/
apt-get install -y bzip2
bunzip2 /opt/eveonline/static/sqlite-latest.sqlite.bz2
