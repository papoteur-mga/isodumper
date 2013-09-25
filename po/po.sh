for i in `ls *.po`
do
msgmerge $i isodumper.pot -o $i 
done
