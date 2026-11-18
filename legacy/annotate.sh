#!/bin/sh

if [ $# -lt 2 ]; then
	echo "Usage: annotate [image-file] [key] ([game-name])"
	exit
fi

BASENAME=${1##*/}
BASENAME=${BASENAME%.*}

INFILE="$1"
OUTFILE=${BASENAME}-NOTED.png
LABEL="$3 [$2] https://koei-wiki.tzengyuxio.me  "
#${file%.*}_sorted.${file##*.}"

# including path
#OUTFILE="${1%.*}_SIG.${1##*.}"

echo $BASENAME
echo $INFILE
echo $OUTFILE
echo $LABEL

convert $INFILE \
	-background navyblue -fill snow \
	-font Menlo-Bold \
	label:"$LABEL" \
	-gravity southeast \
	-append $OUTFILE
