#!/usr/bin/env python3
"""Generate mac/Pinball.xcodeproj for the Mac Catalyst build.

The macOS side of DynoSprite is an Objective-C reimplementation of the engine
(mac/dynosprite/, taken from the space-bandits project) running on SpriteKit.
It compiles the very same game sources as the CoCo build -- game/objects/*.c
and game/levels/*.c -- against a header that turns RegisterObject into a
registry call instead of an object descriptor table.

The project file is generated rather than maintained by hand because the game's
assets are themselves generated: adding a sprite group or a level should not
mean hand-editing a pbxproj.  Playfield assets are attached as folder
references, so their contents land in the bundle as levels/, sprites/, tiles/,
images/ and sounds/ -- exactly where the resource controller looks -- without
one entry per file.

    scripts/gen-xcode.py
"""

import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAC = os.path.join(ROOT, "mac")
PROJECT = os.path.join(MAC, "Pinball.xcodeproj")

TARGET_NAME = "Lost World Pinball"
BUNDLE_ID = "com.jamiecho.LostWorldPinball"


def _version():
    """The version lives in package.json, which is what CI bumps."""
    import json

    with open(os.path.join(ROOT, "package.json")) as f:
        return json.load(f)["version"]


VERSION = _version()

# DSWindowController is AppKit-only and is excluded from the Catalyst app,
# exactly as it is in the project this engine came from.
ENGINE_EXCLUDE = {"DSWindowController.m"}

FILE_TYPES = {
    ".m": ("lastKnownFileType", "sourcecode.c.objc"),
    ".mm": ("lastKnownFileType", "sourcecode.cpp.objcpp"),
    ".c": ("lastKnownFileType", "sourcecode.c.c"),
    ".h": ("lastKnownFileType", "sourcecode.c.h"),
    ".json": ("lastKnownFileType", "text.json"),
    ".html": ("lastKnownFileType", "text.html"),
    ".sks": ("lastKnownFileType", "file.sks"),
    ".ttf": ("lastKnownFileType", "file"),
    ".storyboard": ("lastKnownFileType", "file.storyboard"),
    ".xcassets": ("lastKnownFileType", "folder.assetcatalog"),
    ".plist": ("lastKnownFileType", "text.plist.xml"),
    ".entitlements": ("lastKnownFileType", "text.plist.entitlements"),
}


# The game's own .c files are compiled as Objective-C++, exactly as
# space-bandits does.  That is not incidental: table_data.h defines its lookup
# tables at file scope, which in C++ have internal linkage and so may appear in
# every translation unit that needs them; as C they would collide at link time.
# The engine's own .c files must stay C, or their symbols get mangled and the
# Objective-C callers cannot find them.
GAME_C = ("explicitFileType", "sourcecode.cpp.objcpp")


def uid(*parts):
    """A stable 24-hex object id, so regenerating does not churn the file."""
    h = hashlib.md5("|".join(parts).encode()).hexdigest().upper()
    return h[:24]


class Project:
    def __init__(self):
        self.objects = []  # (uid, comment, body)
        self.sources = []  # build file uids
        self.resources = []

    def add(self, oid, comment, body):
        self.objects.append((oid, comment, body))

    # -- file references ---------------------------------------------------

    def file_ref(self, path, name=None, tree="SOURCE_ROOT", explicit=None):
        name = name or os.path.basename(path)
        oid = uid("ref", path)
        ext = os.path.splitext(name)[1]
        if explicit:
            key, kind = explicit
        else:
            key, kind = FILE_TYPES.get(ext, ("lastKnownFileType", "text"))
        body = (
            f"{{isa = PBXFileReference; {key} = {kind}; name = {q(name)}; "
            f"path = {q(path)}; sourceTree = {tree}; }}"
        )
        self.add(oid, name, body)
        return oid, name

    def folder_ref(self, path):
        """A blue folder: copied into the bundle whole, keeping its name."""
        return self.file_ref(
            path, explicit=("lastKnownFileType", "folder")
        )

    # -- build files -------------------------------------------------------

    def build_file(self, ref, phase):
        oid = uid("build", ref[1], phase)
        body = f"{{isa = PBXBuildFile; fileRef = {ref[0]} /* {ref[1]} */; }}"
        self.add(oid, f"{ref[1]} in {phase}", body)
        return oid, f"{ref[1]} in {phase}"

    def add_source(self, path, explicit=None):
        ref = self.file_ref(path, explicit=explicit)
        self.sources.append(self.build_file(ref, "Sources"))
        return ref

    def add_resource(self, ref):
        self.resources.append(self.build_file(ref, "Resources"))
        return ref


def q(s):
    """Quote a pbxproj value if it is not a bare identifier."""
    if s and all(c.isalnum() or c in "_./$" for c in s):
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def listing(items, indent=4):
    pad = "\t" * indent
    return "".join(f"{pad}{oid} /* {comment} */,\n" for oid, comment in items)


def scan(directory, exts):
    if not os.path.isdir(directory):
        return []
    return sorted(
        f for f in os.listdir(directory) if os.path.splitext(f)[1] in exts
    )


PROJECT_SETTINGS = """				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				CLANG_ENABLE_OBJC_WEAK = YES;
				CLANG_WARN_BOOL_CONVERSION = YES;
				CLANG_WARN_CONSTANT_CONVERSION = YES;
				CLANG_WARN_DIRECT_OBJC_ISA_USAGE = YES_ERROR;
				CLANG_WARN_EMPTY_BODY = YES;
				CLANG_WARN_ENUM_CONVERSION = YES;
				CLANG_WARN_INFINITE_RECURSION = YES;
				CLANG_WARN_INT_CONVERSION = YES;
				CLANG_WARN_OBJC_ROOT_CLASS = YES_ERROR;
				CLANG_WARN_STRICT_PROTOTYPES = YES;
				CLANG_WARN_SUSPICIOUS_MOVE = YES;
				CLANG_WARN_UNREACHABLE_CODE = YES;
				CLANG_WARN__DUPLICATE_METHOD_MATCH = YES;
				COPY_PHASE_STRIP = NO;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				ENABLE_USER_SCRIPT_SANDBOXING = NO;
				GCC_C_LANGUAGE_STANDARD = gnu17;
				GCC_NO_COMMON_BLOCKS = YES;
				GCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR;
				GCC_WARN_UNDECLARED_SELECTOR = YES;
				GCC_WARN_UNUSED_FUNCTION = YES;
				GCC_WARN_UNUSED_VARIABLE = YES;
				HEADER_SEARCH_PATHS = "$(SRCROOT)/dynosprite/include";
				IPHONEOS_DEPLOYMENT_TARGET = 15.0;
				MTL_FAST_MATH = YES;
				SDKROOT = iphoneos;
"""

DEBUG_ONLY = """				DEBUG_INFORMATION_FORMAT = dwarf;
				ENABLE_TESTABILITY = YES;
				GCC_DYNAMIC_NO_PIC = NO;
				GCC_OPTIMIZATION_LEVEL = 0;
				GCC_PREPROCESSOR_DEFINITIONS = (
					"DEBUG=1",
					"$(inherited)",
				);
				MTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;
				ONLY_ACTIVE_ARCH = YES;
"""

RELEASE_ONLY = """				DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
				ENABLE_NS_ASSERTIONS = NO;
				MTL_ENABLE_DEBUG_INFO = NO;
				SWIFT_COMPILATION_MODE = wholemodule;
				VALIDATE_PRODUCT = YES;
"""

TARGET_SETTINGS = f"""				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;
				CODE_SIGN_ENTITLEMENTS = "Pinball/Pinball.entitlements";
				"CODE_SIGN_IDENTITY[sdk=macosx*]" = "-";
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = {VERSION};
				GENERATE_INFOPLIST_FILE = YES;
				INFOPLIST_FILE = "Pinball-Info.plist";
				INFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents = YES;
				INFOPLIST_KEY_UILaunchStoryboardName = Main.storyboard;
				INFOPLIST_KEY_UIMainStoryboardFile = Main;
				INFOPLIST_KEY_UIStatusBarHidden = YES;
				INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad = "UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight";
				INFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone = "UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight";
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MACOSX_DEPLOYMENT_TARGET = 11.0;
				MARKETING_VERSION = {VERSION};
				PRODUCT_BUNDLE_IDENTIFIER = "{BUNDLE_ID}";
				PRODUCT_NAME = "$(TARGET_NAME)";
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SUPPORTS_MACCATALYST = YES;
				SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD = NO;
				TARGETED_DEVICE_FAMILY = "1,2";
"""


def build():
    p = Project()

    # --- engine ------------------------------------------------------------
    engine_src = os.path.join(MAC, "dynosprite", "src")
    engine_refs = []
    for f in scan(engine_src, {".m", ".mm", ".c"}):
        if f in ENGINE_EXCLUDE:
            engine_headers_only = p.file_ref(f"dynosprite/src/{f}")
            engine_refs.append(engine_headers_only)
            continue
        engine_refs.append(p.add_source(f"dynosprite/src/{f}"))
    engine_headers = [
        p.file_ref(f"dynosprite/src/{f}") for f in scan(engine_src, {".h"})
    ]
    engine_headers += [
        p.file_ref(f"dynosprite/include/{f}")
        for f in scan(os.path.join(MAC, "dynosprite", "include"), {".h"})
    ]

    # --- the game, shared verbatim with the CoCo build ----------------------
    game_refs = []
    for f in scan(os.path.join(ROOT, "game", "objects"), {".c"}):
        game_refs.append(p.add_source(f"../game/objects/{f}", explicit=GAME_C))
    for f in scan(os.path.join(ROOT, "game", "levels"), {".c"}):
        game_refs.append(p.add_source(f"../game/levels/{f}", explicit=GAME_C))
    game_headers = [
        p.file_ref(f"../game/objects/{f}")
        for f in scan(os.path.join(ROOT, "game", "objects"), {".h"})
    ]

    # --- application shell --------------------------------------------------
    app_refs = [p.add_source("Pinball/main.m")]
    app_support = [
        p.file_ref("Pinball-Info.plist"),
        p.file_ref("Pinball/Pinball.entitlements"),
    ]

    # --- resources ----------------------------------------------------------
    for path in (
        "dynosprite/src/Actions.sks",
        "dynosprite/Fonts/pcgfont.ttf",
        "Pinball/Assets.xcassets",
        "Pinball/Base.lproj/Main.storyboard",
        "Pinball/Credits.html",
        "../game/defaults-config.json",
    ):
        p.add_resource(p.file_ref(path))

    # Playfield assets, attached whole so the bundle gets levels/, sprites/,
    # tiles/, images/ and sounds/ without an entry per file.
    asset_refs = []
    for folder in ("levels", "sprites", "tiles", "images", "sounds"):
        ref = p.folder_ref(f"../game/{folder}")
        asset_refs.append(ref)
        p.add_resource(ref)

    # --- groups -------------------------------------------------------------
    product_ref = uid("product")
    p.add(
        product_ref,
        f"{TARGET_NAME}.app",
        "{isa = PBXFileReference; explicitFileType = wrapper.application; "
        f"includeInIndex = 0; path = {q(TARGET_NAME + '.app')}; "
        "sourceTree = BUILT_PRODUCTS_DIR; }",
    )

    def group(name, children, gid=None):
        gid = gid or uid("group", name)
        body = (
            "{\n\t\t\tisa = PBXGroup;\n\t\t\tchildren = (\n"
            + listing(children)
            + f"\t\t\t);\n\t\t\tname = {q(name)};\n\t\t\tsourceTree = \"<group>\";\n\t\t}}"
        )
        p.add(gid, name, body)
        return gid, name

    g_engine = group("dynosprite", engine_refs + engine_headers)
    g_game = group("game", game_refs + game_headers + asset_refs)
    g_app = group("Pinball", app_refs + app_support)
    g_products = group("Products", [(product_ref, f"{TARGET_NAME}.app")])
    main_group = uid("maingroup")
    p.add(
        main_group,
        None,
        "{\n\t\t\tisa = PBXGroup;\n\t\t\tchildren = (\n"
        + listing([g_app, g_game, g_engine, g_products])
        + "\t\t\t);\n\t\t\tsourceTree = \"<group>\";\n\t\t}",
    )

    # --- build phases -------------------------------------------------------
    sources_phase = uid("phase", "sources")
    p.add(
        sources_phase,
        "Sources",
        "{\n\t\t\tisa = PBXSourcesBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n"
        "\t\t\tfiles = (\n" + listing(p.sources) + "\t\t\t);\n"
        "\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t}",
    )
    frameworks_phase = uid("phase", "frameworks")
    p.add(
        frameworks_phase,
        "Frameworks",
        "{\n\t\t\tisa = PBXFrameworksBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n"
        "\t\t\tfiles = (\n\t\t\t);\n"
        "\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t}",
    )
    resources_phase = uid("phase", "resources")
    p.add(
        resources_phase,
        "Resources",
        "{\n\t\t\tisa = PBXResourcesBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n"
        "\t\t\tfiles = (\n" + listing(p.resources) + "\t\t\t);\n"
        "\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t}",
    )
    credits_phase = uid("phase", "credits")
    p.add(
        credits_phase,
        "Create Credits",
        "{\n\t\t\tisa = PBXShellScriptBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n"
        "\t\t\tfiles = (\n\t\t\t);\n"
        "\t\t\tinputPaths = (\n\t\t\t\t\"$(SRCROOT)/../game/readme-bas.txt\",\n\t\t\t);\n"
        "\t\t\tname = \"Create Credits\";\n"
        "\t\t\toutputPaths = (\n"
        "\t\t\t\t\"$(TARGET_BUILD_DIR)/$UNLOCALIZED_RESOURCES_FOLDER_PATH/Credits.rtf\",\n"
        "\t\t\t);\n"
        "\t\t\trunOnlyForDeploymentPostprocessing = 0;\n"
        "\t\t\tshellPath = /bin/sh;\n"
        "\t\t\tshellScript = \"sed 1,3d \\\"$SCRIPT_INPUT_FILE_0\\\" | "
        "textutil -convert rtf -stdin -output \\\"$SCRIPT_OUTPUT_FILE_0\\\"\\n\";\n\t\t}",
    )

    # --- configurations -----------------------------------------------------
    def config(name, settings, label):
        cid = uid("config", label, name)
        body = (
            "{\n\t\t\tisa = XCBuildConfiguration;\n\t\t\tbuildSettings = {\n"
            + settings
            + f"\t\t\t}};\n\t\t\tname = {name};\n\t\t}}"
        )
        p.add(cid, name, body)
        return cid, name

    proj_debug = config("Debug", PROJECT_SETTINGS + DEBUG_ONLY, "project")
    proj_release = config("Release", PROJECT_SETTINGS + RELEASE_ONLY, "project")
    tgt_debug = config("Debug", TARGET_SETTINGS, "target")
    tgt_release = config("Release", TARGET_SETTINGS, "target")

    def config_list(label, configs):
        lid = uid("configlist", label)
        body = (
            "{\n\t\t\tisa = XCConfigurationList;\n\t\t\tbuildConfigurations = (\n"
            + listing(configs)
            + "\t\t\t);\n\t\t\tdefaultConfigurationIsVisible = 0;\n"
            "\t\t\tdefaultConfigurationName = Release;\n\t\t}"
        )
        p.add(lid, label, body)
        return lid

    proj_configs = config_list("project", [proj_debug, proj_release])
    tgt_configs = config_list("target", [tgt_debug, tgt_release])

    # --- target and project -------------------------------------------------
    target = uid("target")
    p.add(
        target,
        TARGET_NAME,
        "{\n\t\t\tisa = PBXNativeTarget;\n"
        f"\t\t\tbuildConfigurationList = {tgt_configs};\n"
        "\t\t\tbuildPhases = (\n"
        + listing(
            [
                (sources_phase, "Sources"),
                (frameworks_phase, "Frameworks"),
                (resources_phase, "Resources"),
                (credits_phase, "Create Credits"),
            ]
        )
        + "\t\t\t);\n\t\t\tbuildRules = (\n\t\t\t);\n\t\t\tdependencies = (\n\t\t\t);\n"
        f"\t\t\tname = {q(TARGET_NAME)};\n\t\t\tproductName = {q(TARGET_NAME)};\n"
        f"\t\t\tproductReference = {product_ref};\n"
        "\t\t\tproductType = \"com.apple.product-type.application\";\n\t\t}",
    )

    root = uid("project")
    p.add(
        root,
        "Project object",
        "{\n\t\t\tisa = PBXProject;\n\t\t\tattributes = {\n"
        "\t\t\t\tBuildIndependentTargetsInParallel = 1;\n"
        "\t\t\t\tLastUpgradeCheck = 1540;\n\t\t\t};\n"
        f"\t\t\tbuildConfigurationList = {proj_configs};\n"
        "\t\t\tdevelopmentRegion = en;\n\t\t\thasScannedForEncodings = 0;\n"
        "\t\t\tknownRegions = (\n\t\t\t\ten,\n\t\t\t\tBase,\n\t\t\t);\n"
        f"\t\t\tmainGroup = {main_group};\n"
        f"\t\t\tproductRefGroup = {g_products[0]};\n"
        "\t\t\tprojectDirPath = \"\";\n\t\t\tprojectRoot = \"\";\n"
        "\t\t\ttargets = (\n" + listing([(target, TARGET_NAME)]) + "\t\t\t);\n\t\t}",
    )

    # --- emit ---------------------------------------------------------------
    out = ["// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tclasses = {\n\t};\n"
           "\tobjectVersion = 56;\n\tobjects = {\n"]
    for oid, comment, body in p.objects:
        tag = f" /* {comment} */" if comment else ""
        out.append(f"\t\t{oid}{tag} = {body};\n")
    out.append("\t};\n" f"\trootObject = {root} /* Project object */;\n" "}\n")

    os.makedirs(PROJECT, exist_ok=True)
    with open(os.path.join(PROJECT, "project.pbxproj"), "w") as f:
        f.write("".join(out))

    print(
        f"mac/Pinball.xcodeproj: {len(p.sources)} sources "
        f"({len(game_refs)} from game/), {len(p.resources)} resources"
    )
    return 0


if __name__ == "__main__":
    sys.exit(build())
