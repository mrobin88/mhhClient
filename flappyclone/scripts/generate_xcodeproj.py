#!/usr/bin/env python3
"""Generate PulseScout.xcodeproj/project.pbxproj from the source tree."""

from __future__ import annotations

import itertools
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_SOURCES = sorted((ROOT / "PulseScout").rglob("*.swift"))
TEST_SOURCES = sorted((ROOT / "PulseScoutTests").rglob("*.swift"))
ASSETS = ROOT / "PulseScout" / "Resources" / "Assets.xcassets"
INFO = ROOT / "PulseScout" / "Resources" / "Info.plist"

ids = (f"{i:024X}" for i in itertools.count(0xA10001))


def nid() -> str:
    return next(ids)


PROJECT = nid()
APP_TARGET = nid()
TEST_TARGET = nid()
APP_PRODUCT = nid()
TEST_PRODUCT = nid()
SOURCES_PHASE_APP = nid()
SOURCES_PHASE_TEST = nid()
RESOURCES_PHASE = nid()
FRAMEWORKS_PHASE = nid()
APP_CONFIG_LIST = nid()
TEST_CONFIG_LIST = nid()
PROJECT_CONFIG_LIST = nid()
APP_DEBUG = nid()
APP_RELEASE = nid()
TEST_DEBUG = nid()
TEST_RELEASE = nid()
PROJECT_DEBUG = nid()
PROJECT_RELEASE = nid()
MAIN_GROUP = nid()
PRODUCTS_GROUP = nid()
ROOT_APP_GROUP = nid()
ROOT_TEST_GROUP = nid()

file_refs: dict[pathlib.Path, str] = {}
build_files: dict[pathlib.Path, str] = {}

for path in APP_SOURCES + TEST_SOURCES + [ASSETS, INFO]:
    file_refs[path] = nid()
    if path.suffix == ".swift" or path.name.endswith(".xcassets"):
        build_files[path] = nid()

# Build nested groups from relative posix paths
Group = dict


def rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


# Explicit groups matching folders
folder_groups = {
    "PulseScout": ROOT_APP_GROUP,
    "PulseScoutTests": ROOT_TEST_GROUP,
}
for folder in [
    "PulseScout/App",
    "PulseScout/Theme",
    "PulseScout/Models",
    "PulseScout/Services",
    "PulseScout/ViewModels",
    "PulseScout/Views",
    "PulseScout/Views/Dashboard",
    "PulseScout/Views/Charts",
    "PulseScout/Views/Alerts",
    "PulseScout/Views/Detail",
    "PulseScout/Views/Paywall",
    "PulseScout/Resources",
]:
    folder_groups[folder] = nid()

children: dict[str, list[tuple[str, str]]] = {key: [] for key in folder_groups}
children["PulseScout"] = []
# populate folder children with subfolders
parent_map = {
    "PulseScout/App": "PulseScout",
    "PulseScout/Theme": "PulseScout",
    "PulseScout/Models": "PulseScout",
    "PulseScout/Services": "PulseScout",
    "PulseScout/ViewModels": "PulseScout",
    "PulseScout/Views": "PulseScout",
    "PulseScout/Resources": "PulseScout",
    "PulseScout/Views/Dashboard": "PulseScout/Views",
    "PulseScout/Views/Charts": "PulseScout/Views",
    "PulseScout/Views/Alerts": "PulseScout/Views",
    "PulseScout/Views/Detail": "PulseScout/Views",
    "PulseScout/Views/Paywall": "PulseScout/Views",
}
for child, parent in parent_map.items():
    children[parent].append(("group", child))

for path in APP_SOURCES + [ASSETS, INFO]:
    parent = path.relative_to(ROOT).parent.as_posix()
    children[parent].append(("file", str(path)))

for path in TEST_SOURCES:
    children["PulseScoutTests"].append(("file", str(path)))


def file_ref_block(path: pathlib.Path) -> str:
    fid = file_refs[path]
    name = path.name
    if path.suffix == ".swift":
        ftype = "sourcecode.swift"
    elif path.suffix == ".plist":
        ftype = "text.plist.xml"
    else:
        ftype = "folder.assetcatalog"
    return f'\t\t{fid} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = {ftype}; path = {name}; sourceTree = "<group>"; }};'


def build_file_block(path: pathlib.Path) -> str:
    return (
        f"\t\t{build_files[path]} /* {path.name} in Sources */ = "
        f"{{isa = PBXBuildFile; fileRef = {file_refs[path]} /* {path.name} */; }};"
        if path.suffix == ".swift"
        else (
            f"\t\t{build_files[path]} /* {path.name} in Resources */ = "
            f"{{isa = PBXBuildFile; fileRef = {file_refs[path]} /* {path.name} */; }};"
        )
    )


def group_block(folder: str, gid: str) -> str:
    name = folder.split("/")[-1]
    entries = []
    for kind, item in children[folder]:
        if kind == "group":
            entries.append(f"\t\t\t\t{folder_groups[item]} /* {item.split('/')[-1]} */,")
        else:
            p = pathlib.Path(item)
            entries.append(f"\t\t\t\t{file_refs[p]} /* {p.name} */,")
    joined = "\n".join(entries)
    path_name = name
    return f"""\t\t{gid} /* {name} */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
{joined}
\t\t\t);
\t\t\tpath = {path_name};
\t\t\tsourceTree = "<group>";
\t\t}};"""


app_source_entries = "\n".join(
    f"\t\t\t\t{build_files[p]} /* {p.name} in Sources */," for p in APP_SOURCES
)
test_source_entries = "\n".join(
    f"\t\t\t\t{build_files[p]} /* {p.name} in Sources */," for p in TEST_SOURCES
)

project_debug_settings = """
				ALWAYS_SEARCH_USER_PATHS = NO;
				ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS = YES;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION = YES_AGGRESSIVE;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				CLANG_ENABLE_OBJC_WEAK = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = dwarf;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				ENABLE_TESTABILITY = YES;
				ENABLE_USER_SCRIPT_SANDBOXING = YES;
				GCC_DYNAMIC_NO_PIC = NO;
				GCC_NO_COMMON_BLOCKS = YES;
				GCC_OPTIMIZATION_LEVEL = 0;
				GCC_PREPROCESSOR_DEFINITIONS = (
					"DEBUG=1",
					"$(inherited)",
				);
				IPHONEOS_DEPLOYMENT_TARGET = 17.0;
				MTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;
				ONLY_ACTIVE_ARCH = YES;
				SDKROOT = iphoneos;
				SWIFT_ACTIVE_COMPILATION_CONDITIONS = "DEBUG $(inherited)";
				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
				SWIFT_VERSION = 5.0;
"""

project_release_settings = """
				ALWAYS_SEARCH_USER_PATHS = NO;
				ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS = YES;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION = YES_AGGRESSIVE;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				CLANG_ENABLE_OBJC_WEAK = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
				ENABLE_NS_ASSERTIONS = NO;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				ENABLE_USER_SCRIPT_SANDBOXING = YES;
				GCC_NO_COMMON_BLOCKS = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 17.0;
				MTL_ENABLE_DEBUG_INFO = NO;
				SDKROOT = iphoneos;
				SWIFT_COMPILATION_MODE = wholemodule;
				SWIFT_VERSION = 5.0;
				VALIDATE_PRODUCT = YES;
"""

app_settings = """
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 1;
				DEVELOPMENT_ASSET_PATHS = "";
				ENABLE_PREVIEWS = YES;
				GENERATE_INFOPLIST_FILE = YES;
				INFOPLIST_FILE = PulseScout/Resources/Info.plist;
				INFOPLIST_KEY_CFBundleDisplayName = PulseScout;
				INFOPLIST_KEY_LSApplicationCategoryType = "public.app-category.finance";
				INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
				INFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents = YES;
				INFOPLIST_KEY_UILaunchScreen_Generation = YES;
				INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad = "UIInterfaceOrientationPortrait UIInterfaceOrientationPortraitUpsideDown UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight";
				INFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone = UIInterfaceOrientationPortrait;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 1.0.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.pulsescout.app;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SUPPORTS_MACCATALYST = NO;
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_STRICT_CONCURRENCY = targeted;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
"""

test_settings = """
				BUNDLE_LOADER = "$(TEST_HOST)";
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 1;
				GENERATE_INFOPLIST_FILE = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 17.0;
				MARKETING_VERSION = 1.0.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.pulsescout.app.tests;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
				TEST_HOST = "$(BUILT_PRODUCTS_DIR)/PulseScout.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)/PulseScout";
"""

group_blocks = "\n".join(group_block(folder, gid) for folder, gid in folder_groups.items())

pbx = f"""// !$*UTF8*$!
{{
	archiveVersion = 1;
	classes = {{
	}};
	objectVersion = 56;
	objects = {{

/* Begin PBXBuildFile section */
{chr(10).join(build_file_block(p) for p in APP_SOURCES + TEST_SOURCES + [ASSETS])}
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
		{APP_PRODUCT} /* PulseScout.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = PulseScout.app; sourceTree = BUILT_PRODUCTS_DIR; }};
		{TEST_PRODUCT} /* PulseScoutTests.xctest */ = {{isa = PBXFileReference; explicitFileType = wrapper.cfbundle; includeInIndex = 0; path = PulseScoutTests.xctest; sourceTree = BUILT_PRODUCTS_DIR; }};
{chr(10).join(file_ref_block(p) for p in APP_SOURCES + TEST_SOURCES + [ASSETS, INFO])}
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
		{FRAMEWORKS_PHASE} /* Frameworks */ = {{
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
 marbles = 0;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
		{MAIN_GROUP} = {{
			isa = PBXGroup;
			children = (
				{ROOT_APP_GROUP} /* PulseScout */,
				{ROOT_TEST_GROUP} /* PulseScoutTests */,
				{PRODUCTS_GROUP} /* Products */,
			);
			sourceTree = "<group>";
		}};
		{PRODUCTS_GROUP} /* Products */ = {{
			isa = PBXGroup;
			children = (
				{APP_PRODUCT} /* PulseScout.app */,
				{TEST_PRODUCT} /* PulseScoutTests.xctest */,
			);
			name = Products;
			sourceTree = "<group>";
		}};
{group_blocks}
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
		{APP_TARGET} /* PulseScout */ = {{
			isa = PBXNativeTarget;
			buildConfigurationList = {APP_CONFIG_LIST} /* Build configuration list for PBXNativeTarget "PulseScout" */;
			buildPhases = (
				{SOURCES_PHASE_APP} /* Sources */,
				{FRAMEWORKS_PHASE} /* Frameworks */,
				{RESOURCES_PHASE} /* Resources */,
 marbles
			);
			buildRules = (
			);
			dependencies = (
			);
			name = PulseScout;
			productName = PulseScout;
			productReference = {APP_PRODUCT} /* PulseScout.app */;
			productType = "com.apple.product-type.application";
		}};
		{TEST_TARGET} /* PulseScoutTests */ = {{
			isa = PBXNativeTarget;
			buildConfigurationList = {TEST_CONFIG_LIST} /* Build configuration list for PBXNativeTarget "PulseScoutTests" */;
			buildPhases = (
				{SOURCES_PHASE_TEST} /* Sources */,
			);
			buildRules = (
			);
			dependencies = (
			);
			name = PulseScoutTests;
			productName = PulseScoutTests;
			productReference = {TEST_PRODUCT} /* PulseScoutTests.xctest */;
			productType = "com.apple.product-type.bundle.unit-test";
		}};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
		{PROJECT} /* Project object */ = {{
			isa = PBXProject;
			attributes = {{
				BuildIndependentTargetsInParallel = 1;
				LastSwiftUpdateCheck = 1540;
				LastUpgradeCheck = 1540;
				TargetAttributes = {{
					{APP_TARGET} = {{
						CreatedOnToolsVersion = 15.4;
					}};
					{TEST_TARGET} = {{
						CreatedOnToolsVersion = 15.4;
						TestTargetID = {APP_TARGET};
					}};
				}};
			}};
			buildConfigurationList = {PROJECT_CONFIG_LIST} /* Build configuration list for PBXProject "PulseScout" */;
			compatibilityVersion = "Xcode 14.0";
			developmentRegion = en;
			hasScannedForEncodings = 0;
			knownRegions = (
				en,
				Base,
			);
			mainGroup = {MAIN_GROUP};
			productRefGroup = {PRODUCTS_GROUP} /* Products */;
			projectDirPath = "";
			projectRoot = "";
			targets = (
				{APP_TARGET} /* PulseScout */,
				{TEST_TARGET} /* PulseScoutTests */,
			);
		}};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
		{RESOURCES_PHASE} /* Resources */ = {{
			isa = PBXResourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				{build_files[ASSETS]} /* Assets.xcassets in Resources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
		{SOURCES_PHASE_APP} /* Sources */ = {{
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
{app_source_entries}
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
		{SOURCES_PHASE_TEST} /* Sources */ = {{
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
{test_source_entries}
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
		{PROJECT_DEBUG} /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{{project_debug_settings}			}};
			name = Debug;
		}};
		{PROJECT_RELEASE} /* Release */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{{project_release_settings}			}};
			name = Release;
		}};
		{APP_DEBUG} /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{{app_settings}			}};
			name = Debug;
		}};
		{APP_RELEASE} /* Release */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{{app_settings}			}};
			name = Release;
		}};
		{TEST_DEBUG} /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{{test_settings}			}};
			name = Debug;
		}};
		{TEST_RELEASE} /* Release */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{{test_settings}			}};
			name = Release;
		}};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
		{PROJECT_CONFIG_LIST} /* Build configuration list for PBXProject "PulseScout" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				{PROJECT_DEBUG} /* Debug */,
				{PROJECT_RELEASE} /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		}};
		{APP_CONFIG_LIST} /* Build configuration list for PBXNativeTarget "PulseScout" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				{APP_DEBUG} /* Debug */,
				{APP_RELEASE} /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		}};
		{TEST_CONFIG_LIST} /* Build configuration list for PBXNativeTarget "PulseScoutTests" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				{TEST_DEBUG} /* Debug */,
				{TEST_RELEASE} /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		}};
/* End XCConfigurationList section */
	}};
	rootObject = {PROJECT} /* Project object */;
}}
"""

# Fix accidental "marbles" typos if any slipped in
pbx = pbx.replace(" marbles = 0;", "").replace(" marbles\n", "\n")

out = ROOT / "PulseScout.xcodeproj" / "project.pbxproj"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(pbx)
print(f"Wrote {out}")
print(f"APP_TARGET={APP_TARGET}")
