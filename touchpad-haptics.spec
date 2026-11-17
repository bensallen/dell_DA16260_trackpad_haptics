Name:           touchpad-haptics
Version:        1.1
Release:        1%{?dist}
Summary:        Control haptic feedback strength on HID haptic touchpads
License:        MIT
BuildArch:      noarch

Source0:        touchpad-haptics
Source1:        70-touchpad-haptics.rules
Source2:        touchpad-haptics.sleep
Source3:        touchpad-haptics.conf

BuildRequires:  systemd-rpm-macros
Requires:       python3
Requires:       systemd-udev

%description
Sets the haptic feedback intensity (HID Haptics page, Intensity usage) on
touchpads that expose it, such as the Synaptics 06CB:D01A in the Dell XPS 16
DA16260. Strength is set as a level (off, 1-4), matching the five steps the
touchpad's haptic controller supports. The configured level is applied when
the device appears and after resume from suspend.

%prep

%build

%install
install -Dpm755 %{SOURCE0} %{buildroot}%{_bindir}/touchpad-haptics
install -Dpm644 %{SOURCE1} %{buildroot}%{_udevrulesdir}/70-touchpad-haptics.rules
install -Dpm755 %{SOURCE2} %{buildroot}%{_systemd_util_dir}/system-sleep/touchpad-haptics
install -Dpm644 %{SOURCE3} %{buildroot}%{_sysconfdir}/touchpad-haptics.conf

%post
udevadm control --reload >/dev/null 2>&1 || :
udevadm trigger --subsystem-match=hidraw --action=add >/dev/null 2>&1 || :

%files
%{_bindir}/touchpad-haptics
%{_udevrulesdir}/70-touchpad-haptics.rules
%{_systemd_util_dir}/system-sleep/touchpad-haptics
%config(noreplace) %{_sysconfdir}/touchpad-haptics.conf

%changelog
* Tue Nov 17 2026 bsallen - 1.1-1
- Use levels off/1-4 instead of raw 0-100 intensity; add set --raw
- Config key is now LEVEL

* Tue Nov 17 2026 bsallen - 1.0-1
- Initial package
