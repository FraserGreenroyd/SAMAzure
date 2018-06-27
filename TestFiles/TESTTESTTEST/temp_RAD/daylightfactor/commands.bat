

cd TESTTESTTEST/temp_RAD/daylightfactor

/usr/local/radiance/bin/gensky 9 21 12 -B 558.659217877 -c > sky/CertainIlluminanceLevel_100000.sky
/usr/local/radiance/bin/oconv -f sky/CertainIlluminanceLevel_100000.sky sky/groundSky.rad scene/opaque/temp_RAD..opq.mat scene/opaque/temp_RAD..opq.rad scene/glazing/temp_RAD..glz.mat scene/glazing/temp_RAD..glz.rad > temp_RAD.oct
/usr/local/radiance/bin/rtrace -I -lr 4 -aa 0.25 -dj 0.0 -ds 0.5 -ss 0.0 -dp 64 -dt 0.5 -ad 512 -st 0.85 -lw 0.05 -as 128 -dc 0.25 -ab 2 -e error.txt -h -dr 3 -ar 16 temp_RAD.oct < temp_RAD.pts > result/temp_RAD.res
/usr/local/radiance/bin/rcalc -e '$1=(0.265*$1+0.67*$2+0.065*$3)*179' result/temp_RAD.res > result/temp_RAD.ill