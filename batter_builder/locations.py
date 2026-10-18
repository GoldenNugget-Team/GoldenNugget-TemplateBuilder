"""Known places to write, offered in the path box.

The plist paths are the ones GoldenNugget's own tweaks use
(src/tweaks/basic_plist_locations.py in the GoldenNugget repository). Keys in
Managed Preferences files are merged with GoldenNugget's keys; anywhere else a
plist write replaces the whole file.
"""

MANAGED = "/var/Managed Preferences/mobile/"

LOCATIONS = (
    (MANAGED + "com.apple.springboard.plist", "SpringBoard (Home and Lock Screen)"),
    (MANAGED + ".GlobalPreferences.plist", "Global preferences (every app)"),
    (MANAGED + "com.apple.UIKit.plist", "UIKit"),
    (MANAGED + "com.apple.backboardd.plist", "backboardd (display, touches)"),
    (MANAGED + "com.apple.AppStore.plist", "App Store"),
    (MANAGED + "com.apple.mobilenotes.plist", "Notes"),
    (MANAGED + "com.apple.Pasteboard.plist", "Pasteboard"),
    (MANAGED + "com.apple.CoreMotion.plist", "Core Motion"),
    (MANAGED + "com.apple.sharingd.plist", "AirDrop (sharingd)"),
    ("/var/mobile/Library/Preferences/", "App preferences (whole file)"),
)

# Files GoldenNugget writes whole itself; a template may not replace them
# while GoldenNugget's own tweaks write them.
GOLDENNUGGET_FILES = frozenset({
    "/var/preferences/FeatureFlags/Global.plist",
    "/var/containers/Shared/SystemGroup/systemgroup.com.apple.configurationprofiles/Library/"
    "ConfigurationProfiles/SharedDeviceConfiguration.plist",
    "/var/mobile/Library/Preferences/com.apple.NanoRegistry.plist",
    "/var/mobile/Library/SpringBoard/StatusBarOverrides.archive",
    "/var/mobile/Library/SpringBoard/statusBarOverrides",
    "/var/mobile/Library/Preferences/.GlobalPreferences.plist",
    "/var/db/com.apple.xpc.launchd/disabled.plist",
    "/var/mobile/Library/Preferences/com.apple.ScreenTimeAgent.plist",
} | {path for path, _ in LOCATIONS if path.endswith(".plist")})
