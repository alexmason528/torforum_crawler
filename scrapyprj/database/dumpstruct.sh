#!/bin/sh
mysqldump -d -p --triggers $1 | sed -e 's/DEFINER[ ]*=[ ]*[^*]*\*/\*/' | sed 's/ AUTO_INCREMENT=[0-9]*\b//'