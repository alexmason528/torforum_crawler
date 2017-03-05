#!/bin/sh
mysqldump -d -p --triggers $1 | sed -e 's/DEFINER[ ]*=[ ]*[^*]*\*/\*/'