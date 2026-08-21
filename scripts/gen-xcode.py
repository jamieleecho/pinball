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

# The engine's unit tests, brought across from space-bandits.  They test the
# engine and not this game, which is why they can be taken verbatim; the two
# that had to be adapted are the ones covering the parts of the engine this
# project changed, the menu and the key matrix.
TESTS_NAME = "dynosprite tests"
TESTS_DIR = "dynosprite tests"
TESTS_BUNDLE_ID = "com.jamiecho.LostWorldPinballTests"

# OCMock sits beside the project rather than inside the test folder, and the
# test plan beside it, which is where Xcode puts them when they are added
# through the IDE.  Both paths are relative to mac/.
TESTS_FRAMEWORK = "Frameworks/OCMock.xcframework"

# The test plan is what CI runs, and it -- not the scheme -- owns the list of
# tests to skip.  A scheme that names a plan hands the whole test action over
# to it, so keeping a second list in the scheme would be a place for the two
# to disagree.
TESTS_PLAN = "dynosprite-github.xctestplan"
TESTS_PLAN_NAME = "dynosprite-github"

# DSWindowController is AppKit-only and out of the Catalyst app, so its test
# cannot build either -- the same exclusion the sibling project makes.
TESTS_EXCLUDE = {"DSWindowControllerTest.m"}


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
    ".png": ("lastKnownFileType", "image.png"),
    ".gif": ("lastKnownFileType", "image.gif"),
    ".tiff": ("lastKnownFileType", "image.tiff"),
    ".wav": ("lastKnownFileType", "audio.wav"),
    ".xcframework": ("lastKnownFileType", "wrapper.xcframework"),
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
        self._seen = {}    # uid -> body, so a shared file ref is emitted once
        self.sources = []  # build file uids
        self.resources = []
        self.test_sources = []
        self.test_resources = []

    def add(self, oid, comment, body):
        """Emit an object once.  A file compiled into both targets shares its
        PBXFileReference, so the same id arrives twice and the second must be
        dropped: a repeated key makes the project unreadable."""
        if oid in self._seen:
            assert self._seen[oid] == body, f"two objects claim id {oid}"
            return
        self._seen[oid] = body
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

    def build_file(self, ref, phase, scope="", settings=None):
        oid = uid("build", ref[1], phase, scope)
        extra = f" settings = {{{settings}}};" if settings else ""
        body = f"{{isa = PBXBuildFile; fileRef = {ref[0]} /* {ref[1]} */;{extra} }}"
        self.add(oid, f"{ref[1]} in {phase}", body)
        return oid, f"{ref[1]} in {phase}"

    def add_source(self, path, explicit=None):
        ref = self.file_ref(path, explicit=explicit)
        self.sources.append(self.build_file(ref, "Sources"))
        return ref

    def add_resource(self, ref):
        self.resources.append(self.build_file(ref, "Resources"))
        return ref

    def add_test_source(self, path, explicit=None):
        ref = self.file_ref(path, explicit=explicit)
        self.test_sources.append(self.build_file(ref, "Sources", "tests"))
        return ref

    def add_test_resource(self, ref):
        self.test_resources.append(self.build_file(ref, "Resources", "tests"))
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


TESTS_SETTINGS = f"""				"CODE_SIGN_IDENTITY[sdk=macosx*]" = "-";
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = {VERSION};
				FRAMEWORK_SEARCH_PATHS = "$(inherited)";
				GENERATE_INFOPLIST_FILE = YES;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
					"@loader_path/Frameworks",
				);
				MACOSX_DEPLOYMENT_TARGET = 11.0;
				MARKETING_VERSION = {VERSION};
				PRODUCT_BUNDLE_IDENTIFIER = "{TESTS_BUNDLE_ID}";
				PRODUCT_NAME = "$(TARGET_NAME)";
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SUPPORTS_MACCATALYST = YES;
				SUPPORTS_MAC_DESIGNED_FOR_IPHONE_IPAD = NO;
				TARGETED_DEVICE_FAMILY = "1,2";
"""


def check_test_plan(tests_target):
    """The plan names its target by object id, which this file invents.

    The id is derived from a fixed string, so it is stable across
    regenerations -- but a rename here would move it, and a test plan pointing
    at a target that no longer exists fails in a way that reads like the tests
    are missing rather than misaddressed.  Say so instead.
    """
    import json

    path = os.path.join(MAC, TESTS_PLAN)
    with open(path) as f:
        plan = json.load(f)
    for entry in plan.get("testTargets", []):
        target = entry.get("target", {})
        if target.get("identifier") != tests_target:
            raise SystemExit(
                f"{TESTS_PLAN} names target {target.get('identifier')}, but the "
                f"'{TESTS_NAME}' target is {tests_target}.  Update the plan."
            )
        if target.get("name") != TESTS_NAME:
            raise SystemExit(
                f"{TESTS_PLAN} names target {target.get('name')!r}, "
                f"expected {TESTS_NAME!r}."
            )


def write_scheme(app_target, tests_target):
    """Write a shared scheme covering both targets.

    Without one, `xcodebuild -scheme` depends on Xcode auto-creating schemes
    from the targets, which is a behaviour of the IDE rather than a promise of
    the build system.  Writing it makes `build` and `test` reproducible, and
    lets one scheme name do both.

    The test action is handed to `dynosprite-github.xctestplan`, which is what
    CI runs and what carries the list of tests to skip.
    """
    def buildable(tid, name, product):
        return (
            '<BuildableReference\n'
            '               BuildableIdentifier = "primary"\n'
            f'               BlueprintIdentifier = "{tid}"\n'
            f'               BuildableName = "{product}"\n'
            f'               BlueprintName = "{name}"\n'
            '               ReferencedContainer = "container:Pinball.xcodeproj">\n'
            '            </BuildableReference>'
        )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1540"
   version = "1.7">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES">
      <BuildActionEntries>
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
            {buildable(app_target, TARGET_NAME, TARGET_NAME + ".app")}
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES">
      <TestPlans>
         <TestPlanReference
            reference = "container:{TESTS_PLAN}"
            default = "YES">
         </TestPlanReference>
      </TestPlans>
      <Testables>
         <TestableReference
            skipped = "NO"
            parallelizable = "YES">
            {buildable(tests_target, TESTS_NAME, TESTS_NAME + ".xctest")}
         </TestableReference>
      </Testables>
   </TestAction>
   <LaunchAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         {buildable(app_target, TARGET_NAME, TARGET_NAME + ".app")}
      </BuildableProductRunnable>
   </LaunchAction>
   <ProfileAction
      buildConfiguration = "Release"
      shouldUseLaunchSchemeArgsEnv = "YES"
      savedToolIdentifier = ""
      useCustomWorkingDirectory = "NO"
      debugDocumentVersioning = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         {buildable(app_target, TARGET_NAME, TARGET_NAME + ".app")}
      </BuildableProductRunnable>
   </ProfileAction>
   <AnalyzeAction
      buildConfiguration = "Debug">
   </AnalyzeAction>
   <ArchiveAction
      buildConfiguration = "Release"
      revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>
"""
    where = os.path.join(PROJECT, "xcshareddata", "xcschemes")
    os.makedirs(where, exist_ok=True)
    with open(os.path.join(where, f"{TARGET_NAME}.xcscheme"), "w") as f:
        f.write(xml)


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

    # --- the engine's unit tests --------------------------------------------
    # The tests compile their own copy of the engine rather than loading the
    # app: they are not hosted, so there is no application to load them into.
    # That is also why the engine sources appear in two Sources phases.
    tests_src = os.path.join(MAC, TESTS_DIR, "src")
    tests_res = os.path.join(MAC, TESTS_DIR, "resources")
    test_refs = []
    for f in scan(engine_src, {".m", ".mm", ".c"}):
        if f in ENGINE_EXCLUDE:
            continue
        p.test_sources.append(
            p.build_file(p.file_ref(f"dynosprite/src/{f}"), "Sources", "tests")
        )
    for f in scan(tests_src, {".m", ".mm"}):
        if f in TESTS_EXCLUDE:
            test_refs.append(p.file_ref(f"{TESTS_DIR}/src/{f}"))
            continue
        test_refs.append(p.add_test_source(f"{TESTS_DIR}/src/{f}"))
    test_headers = [
        p.file_ref(f"{TESTS_DIR}/src/{f}") for f in scan(tests_src, {".h"})
    ]

    # Fixtures are attached one by one, not as a folder: the tests look them up
    # with pathForResource:, which only finds them at the top of the bundle.
    test_res_refs = []
    for f in sorted(os.listdir(tests_res)):
        if f.startswith("."):
            continue
        full = os.path.join(tests_res, f)
        if os.path.isdir(full):
            ref = p.folder_ref(f"{TESTS_DIR}/resources/{f}")
        else:
            ref = p.file_ref(f"{TESTS_DIR}/resources/{f}")
        test_res_refs.append(ref)
        p.add_test_resource(ref)
    for path in ("dynosprite/Fonts/pcgfont.ttf", "dynosprite/src/Actions.sks"):
        p.add_test_resource(p.file_ref(path))

    ocmock = p.file_ref(TESTS_FRAMEWORK)
    tests_link = p.build_file(ocmock, "Frameworks", "tests")
    # An embedded framework has to be signed as it is copied, or the test
    # bundle will not load it.
    tests_copy = p.build_file(
        ocmock,
        "Copy Frameworks",
        "tests",
        settings="ATTRIBUTES = (CodeSignOnCopy, RemoveHeadersOnCopy, ); ",
    )

    test_plan = p.file_ref(TESTS_PLAN)
    p.add_test_resource(test_plan)

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

    tests_product_ref = uid("product", "tests")
    p.add(
        tests_product_ref,
        f"{TESTS_NAME}.xctest",
        "{isa = PBXFileReference; explicitFileType = wrapper.cfbundle; "
        f"includeInIndex = 0; path = {q(TESTS_NAME + '.xctest')}; "
        "sourceTree = BUILT_PRODUCTS_DIR; }",
    )

    g_engine = group("dynosprite", engine_refs + engine_headers)
    g_game = group("game", game_refs + game_headers + asset_refs)
    g_app = group("Pinball", app_refs + app_support)
    g_tests = group(
        TESTS_NAME,
        test_refs + test_headers + test_res_refs + [ocmock, test_plan],
    )
    g_products = group(
        "Products",
        [
            (product_ref, f"{TARGET_NAME}.app"),
            (tests_product_ref, f"{TESTS_NAME}.xctest"),
        ],
    )
    main_group = uid("maingroup")
    p.add(
        main_group,
        None,
        "{\n\t\t\tisa = PBXGroup;\n\t\t\tchildren = (\n"
        + listing([g_app, g_game, g_engine, g_tests, g_products])
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

    tests_sources_phase = uid("phase", "tests-sources")
    p.add(
        tests_sources_phase,
        "Sources",
        "{\n\t\t\tisa = PBXSourcesBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n"
        "\t\t\tfiles = (\n" + listing(p.test_sources) + "\t\t\t);\n"
        "\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t}",
    )
    tests_frameworks_phase = uid("phase", "tests-frameworks")
    p.add(
        tests_frameworks_phase,
        "Frameworks",
        "{\n\t\t\tisa = PBXFrameworksBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n"
        "\t\t\tfiles = (\n" + listing([tests_link]) + "\t\t\t);\n"
        "\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t}",
    )
    # OCMock is a dynamic framework, so it has to travel inside the .xctest
    # bundle; linking it is not enough to find it at run time.
    tests_copy_phase = uid("phase", "tests-copy")
    p.add(
        tests_copy_phase,
        "Copy Frameworks",
        "{\n\t\t\tisa = PBXCopyFilesBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n"
        "\t\t\tdstPath = \"\";\n\t\t\tdstSubfolderSpec = 10;\n"
        "\t\t\tfiles = (\n" + listing([tests_copy]) + "\t\t\t);\n"
        "\t\t\tname = \"Copy Frameworks\";\n"
        "\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t}",
    )
    tests_resources_phase = uid("phase", "tests-resources")
    p.add(
        tests_resources_phase,
        "Resources",
        "{\n\t\t\tisa = PBXResourcesBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n"
        "\t\t\tfiles = (\n" + listing(p.test_resources) + "\t\t\t);\n"
        "\t\t\trunOnlyForDeploymentPostprocessing = 0;\n\t\t}",
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

    tests_debug = config("Debug", TESTS_SETTINGS, "tests")
    tests_release = config("Release", TESTS_SETTINGS, "tests")

    proj_configs = config_list("project", [proj_debug, proj_release])
    tgt_configs = config_list("target", [tgt_debug, tgt_release])
    tests_configs = config_list("tests", [tests_debug, tests_release])

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

    tests_target = uid("target", "tests")
    p.add(
        tests_target,
        TESTS_NAME,
        "{\n\t\t\tisa = PBXNativeTarget;\n"
        f"\t\t\tbuildConfigurationList = {tests_configs};\n"
        "\t\t\tbuildPhases = (\n"
        + listing(
            [
                (tests_sources_phase, "Sources"),
                (tests_frameworks_phase, "Frameworks"),
                (tests_copy_phase, "Copy Frameworks"),
                (tests_resources_phase, "Resources"),
            ]
        )
        + "\t\t\t);\n\t\t\tbuildRules = (\n\t\t\t);\n\t\t\tdependencies = (\n\t\t\t);\n"
        f"\t\t\tname = {q(TESTS_NAME)};\n\t\t\tproductName = {q(TESTS_NAME)};\n"
        f"\t\t\tproductReference = {tests_product_ref};\n"
        "\t\t\tproductType = \"com.apple.product-type.bundle.unit-test\";\n\t\t}",
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
        "\t\t\ttargets = (\n"
        + listing([(target, TARGET_NAME), (tests_target, TESTS_NAME)])
        + "\t\t\t);\n\t\t}",
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

    check_test_plan(tests_target)
    write_scheme(target, tests_target)

    print(
        f"mac/Pinball.xcodeproj: {len(p.sources)} sources "
        f"({len(game_refs)} from game/), {len(p.resources)} resources; "
        f"{TESTS_NAME}: {len(p.test_sources)} sources, "
        f"{len(p.test_resources)} resources"
    )
    return 0


if __name__ == "__main__":
    sys.exit(build())
