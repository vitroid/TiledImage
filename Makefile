all:
	echo Hello.
#%: temp_%
#	genice -h | python3 Utilities/replace.py %%usage%% "    " $< > $@
%.rst: %.md
	md2rst $<
install:
	./setup.py install
uninstall:
	pip3 uninstall TiledImage
pypi:
	make README.rst
	./setup.py check
	./setup.py sdist bdist_wheel upload
test:
	2pngs sample.png sample.pngs 39
	pngs2 sample.pngs sample.jpg
distclean:
	-rm *.scad *.yap @*
	-rm -rf build dist
	-rm -rf GenIce.egg-info
	-rm README.rst
