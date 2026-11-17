TOPDIR := $(CURDIR)/rpmbuild

.PHONY: rpm srpm clean

rpm:
	rpmbuild -ba --define "_topdir $(TOPDIR)" --define "_sourcedir $(CURDIR)" touchpad-haptics.spec

srpm:
	rpmbuild -bs --define "_topdir $(TOPDIR)" --define "_sourcedir $(CURDIR)" touchpad-haptics.spec

clean:
	rm -rf $(TOPDIR)
