#!/usr/bin/env bash


cd HoneybeeRecipeJSONs/zone1/daylightfactor

../../../radiance-5.1.0-Linux/usr/local/radiance/bin/gensky 9 21 12 -B 558.659217877 -c > sky/CertainIlluminanceLevel_100000.sky
../../../radiance-5.1.0-Linux/usr/local/radiance/bin/rtrace -I -lr 4 -aa 0.25 -dj 0.0 -ds 0.5 -ss 0.0 -dp 64 -dt 0.5 -ad 512 -st 0.85 -lw 0.05 -as 128 -dc 0.25 -ab 2 -e error.txt -h -dr 3 -ar 16 ../../../zone1.oct < ../../../zone1.pts > result/zone1.res
../../../radiance-5.1.0-Linux/usr/local/radiance/bin/rcalc -e '$1=(0.265*$1+0.67*$2+0.065*$3)*179' result/zone1.res > result/zone1.ill