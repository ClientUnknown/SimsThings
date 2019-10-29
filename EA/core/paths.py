import argparseimport os.pathimport sims4.resourcestry:
    import __app_paths__
except ImportError:

    class __app_paths__:

        @staticmethod
        def configure_app_paths(pathroot, from_archive, user_script_roots, layers):
            pass
IS_ARCHIVE = FalseDEBUG_AVAILABLE = FalseLOCAL_WORK_ENABLED = FalseDATA_ROOT = NoneAPP_ROOT = NoneSCRIPT_ROOT = NoneUSER_SCRIPT_ROOTS = NoneTUNING_ROOTS = NoneLAYERS = None_CORE = NoneAUTOMATION_MODE = FalseSUPPORT_RELOADING_RESOURCES = FalseIS_DESKTOP = TrueDUMP_ROOT = None
def init(pathroot, localwork, from_archive, deploy_override=None, app_directory=None, debug_available=False, local_work_enabled=False, automation_mode=False, dump_root=None):
    global IS_ARCHIVE, APP_ROOT, DEBUG_AVAILABLE, AUTOMATION_MODE, DATA_ROOT, TUNING_ROOTS, SCRIPT_ROOT, _CORE, USER_SCRIPT_ROOTS, LAYERS, DUMP_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument('--enable_tuning_reload', default=False, action='store_true', help='Enable the tuning reload hooks')
    (args, unused_args) = parser.parse_known_args()
    IS_ARCHIVE = from_archive
    APP_ROOT = app_directory
    if debug_available:
        try:
            import pydevd
            import debugger
            DEBUG_AVAILABLE = True
        except ImportError:
            pass
    AUTOMATION_MODE = automation_mode
    pathroot = os.path.abspath(os.path.normpath(pathroot + os.path.sep))
    DATA_ROOT = os.path.join(pathroot, 'Data')
    TUNING_ROOTS = {}
    for definition in sims4.resources.INSTANCE_TUNING_DEFINITIONS:
        TUNING_ROOTS[definition.resource_type] = os.path.join(DATA_ROOT, definition.TypeNames)
    if not from_archive:
        SCRIPT_ROOT = os.path.join(pathroot, 'Scripts')
        core_path = os.path.join(pathroot, 'Scripts', 'Core')
        lib_path = os.path.join(pathroot, 'Scripts', 'lib')
        debug_path = os.path.join(pathroot, 'Scripts', 'Debug')
        tests_path = os.path.join(pathroot, 'Scripts', 'Tests')
        build_path = os.path.join(pathroot, 'Scripts', 'Build')
        native_tuning_path = os.path.join(pathroot, 'Scripts', 'NativeTuning')
    else:
        SCRIPT_ROOT = None
        core_path = os.path.join(pathroot, 'Gameplay', 'core.zip')
        lib_path = os.path.join(pathroot, 'Gameplay', 'lib.zip')
        debug_path = os.path.join(pathroot, 'Gameplay', 'debug.zip')
        tests_path = os.path.join(pathroot, 'Gameplay', 'tests.zip')
        build_path = os.path.join(pathroot, 'Gameplay', 'build.zip')
        native_tuning_path = os.path.join(pathroot, 'Gameplay', 'nativetuning.zip')
    _CORE = core_path
    google_path = os.path.join(core_path, 'google')
    dll_path = os.path.join(app_directory, 'Python', 'DLLs')
    generated_path = os.path.join(app_directory, 'Python', 'Generated')
    deployed_path = deploy_override if deploy_override else os.path.join(app_directory, 'Python', 'Deployed')
    USER_SCRIPT_ROOTS = [core_path]
    LAYERS = [dll_path, lib_path, google_path, os.path.join(core_path, 'api_config.py'), generated_path, deployed_path, debug_path, core_path]
    __app_paths__.configure_app_paths(pathroot, from_archive, USER_SCRIPT_ROOTS, LAYERS)
    LAYERS += [tests_path, build_path, native_tuning_path]
    if dump_root:
        DUMP_ROOT = dump_root
    else:
        DUMP_ROOT = '.'
    from sims4.tuning.merged_tuning_manager import create_manager, get_manager
    create_manager()
    mtg = get_manager()
    mtg.load()
