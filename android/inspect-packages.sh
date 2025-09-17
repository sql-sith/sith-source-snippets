#!/bin/sh

printf "\nList all currently-running services:\n"
dumpsys -l

printf "\nList all installed services:\n"
for pkg in $(pm list packages -3 | cut -f2 -d:); do
  dumpsys package "$pkg" | grep -E "Service" | sed "s/^/[$pkg] /"
done

printf "\nList all packages:\n"
pm list packages

printf "\nList all third-party packages (anything not part of the"
printf "\nsystem image):\n"
dumpsys package -3 -l | sort

printf "\nList all packages, along with their installer, and filter"
printf "\nout ones that are not from the Play Store.\n"
pm list packages -i -3 | 
  grep -v 'installer=com.android.vending' | 
  cut -f 1 -d ':' | cut -f 1 -d ' ' |
  sort

# List all third‑party (non‑system) packages that declare Android Auto compatibility.
# Detection is based on one of three manifest/service identifiers:
#
#   - CarAppService                          → current AndroidX Car App Library (nav/messaging)
#   - MediaBrowserService                    → media apps (music/podcasts/audiobooks)
#   - com.google.android.gms.car.application → legacy nav/messaging meta‑data tag
#
# Note: Some legacy apps declare only the meta‑data tag pointing to an external
#       automotive_app_desc.xml resource. In those cases, `dumpsys` will not show
#       the string "com.google.android.gms.car.application" — catching them would
#       require pulling and inspecting the APK.

for pkg in $(pm list packages -3 -i | grep -v com.android.vending | cut -f2 -d: | cut -f1 -d" "); do
  if dumpsys package $pkg 2>/dev/null | grep -q "CarAppService"; then
    label=$(dumpsys package $pkg | grep -m1 "application-label:" | cut -d: -f2-)
    echo "NAV: $label ($pkg)"
  elif dumpsys package $pkg 2>/dev/null | grep -q "MediaBrowserService"; then
    label=$(dumpsys package $pkg | grep -m1 "application-label:" | cut -d: -f2-)
    echo "MEDIA: $label ($pkg)"
  elif dumpsys package $pkg 2>/dev/null | grep -q "com.google.android.gms.car.application"; then
    label=$(dumpsys package $pkg | grep -m1 "application-label:" | cut -d: -f2-)
    echo "LEGACY: $label ($pkg)"
  fi
done | sort -u

# simpler version of above - no ancient apps:
for pkg in $(pm list packages -3 -i | grep -v com.android.vending | cut -f2 -d: | cut -f1 -d" "); do
  if dumpsys package $pkg 2>/dev/null | grep -q "CarAppService"; then
    label=$(dumpsys package $pkg | grep -m1 "application-label:" | cut -d: -f2-)
    echo "NAV: $label ($pkg)"
  elif dumpsys package $pkg 2>/dev/null | grep -q "MediaBrowserService"; then
    label=$(dumpsys package $pkg | grep -m1 "application-label:" | cut -d: -f2-)
    echo "MEDIA: $label ($pkg)"
  fi
done | sort -u

# simpler version of above - no labels, no ancient apps
for pkg in $(pm list packages -3 -i | 
grep -v com.android.vending | cut -f2 -d: | cut -f1 -d" "); do
  if dumpsys package "$pkg" 2>/dev/null | grep -qE "CarAppService|MediaBrowserService"; then
    label=$(dumpsys package "$pkg" | grep -m1 "application-label:" | cut -d: -f2-)
    echo "$label ($pkg)"
  fi
done | sort -u


