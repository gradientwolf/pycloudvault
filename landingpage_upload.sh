#!/bin/sh
start=`date +%s`
echo "Purge directory indices"
find ./ -iname "index.html" -delete

echo "Generating indices and encrypting frontpage..."
python3 encrypt_indexpage.py ./ --password $1 --verbose

echo "Sync with Google Cloud Storage..."
gsutil -m rsync -r -d . gs://your-bucket-name

end=`date +%s`
echo "Operation completed in $(($end-$start))s"
