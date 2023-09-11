import getpass
import os
from namedpath import NamedPathTree, PathContextError
import pytest
import tempfile

ROOT = os.path.join(tempfile.gettempdir(), 'my_struct')
CURRENT_USER = getpass.getuser()


@pytest.fixture()
def patterns():
    return dict(
        PROJECT='{PROJECT_NAME}',
            SHOTS='[PROJECT]/shot',
                SHOT='[SHOTS]/{ENTITY_NAME}',
                    SHOT_PUBLISH={
                        'path': '[SHOT]/publish/v{VERSION:03d}/{ENTITY_NAME}_v{VERSION:03d}.{EXT}',
                        "groups": [None, CURRENT_USER, None],
                        "users": [CURRENT_USER, None, "root"],
                        "types": {"VERSION": "int"}
                    },
            ASSETS='[PROJECT]/assets',
                ASSET={'path': '[ASSETS]/{ENTITY_NAME}', 'preset': 'USER_DIR'},
                    ASSET_MODELS='[ASSET]/models',
        option_presets={
            "USER_DIR": {"perm": "755", "user": "test"}
        }
    )


@pytest.fixture()
def context():
    return dict(
        project_name='example',
        entity_name='sh001',
        version=15,
        ext='exr'
    )


@pytest.fixture()
def tree(patterns):
    return NamedPathTree(ROOT, patterns)


@pytest.fixture()
def path_ctl1(tree):
    return tree.get_path_instance('SHOT_PUBLISH')


@pytest.fixture()
def path_ctl2(tree):
    return tree.get_path_instance('ASSET_MODELS')


def test_unique_patterns(tree, context):
    tree.check_uniqueness_of_parsing(context)


def test_pattern_creation(tree, patterns):
    assert set(tree.get_path_names()) == set(patterns.keys())


def test_paths_solving(tree, context):
    assert tree.get_path('PROJECT', context) == os.path.normpath(os.path.join(ROOT, 'example'))
    p1 = tree.get_path('SHOT_PUBLISH', context)
    p2 = os.path.normpath(os.path.join(ROOT, 'example/shot/sh001/publish/v015/sh001_v015.exr'))
    assert p1 == p2


def test_parsing_name(tree, context):
    path1 = tree.get_path('SHOT', context)
    name = tree.parse(path1)
    assert name == 'SHOT'


def test_parsing_context(context, path_ctl1):
    assert path_ctl1.parse(path_ctl1.solve(context)) == context


def test_tree_props(tree):
    assert tree.path == '/tmp/my_struct'
    assert tree.get_path_names() == ('ASSET', 'ASSETS', 'ASSET_MODELS', 'PROJECT', 'SHOT', 'SHOTS', 'SHOT_PUBLISH')
    assert tree.get_path_instance('ASSET').name == 'ASSET'


def test_path_instance_parent_object(path_ctl1, tree, context):
    parent = tree.get_path_instance('SHOT')
    assert path_ctl1.get_parent() is parent


def test_path_instance_parent_name(path_ctl1, context):
    assert path_ctl1.get_parent_name() == 'SHOT'


def test_path_instance_parent_names(path_ctl1, context):
    assert path_ctl1.get_all_parent_names() == ['PROJECT', 'SHOTS', 'SHOT']


def test_path_glob_pattern(path_ctl1):
    assert path_ctl1.as_glob() == '*/shot/*/publish/v*/*_v*.*'


def test_path_regex_pattern(path_ctl1):
    pat = path_ctl1.as_regex()
    assert pat == r'^(?P<project_name>[^/\\]+)/shot/(?P<entity_name>[^/\\]+)/publish/v(?P<version>[^/\\]+)/[^/\\]+_v[^/\\]+\.(?P<ext>[^/\\]+)$'


def test_path_permissions_list(path_ctl1):
    assert path_ctl1.get_permission_list() == [493, 493, 493]
    assert path_ctl1.get_permission_list(default_permission=0o775) == [509, 509, 509]


def test_path_group_list(path_ctl1, path_ctl2):
    assert path_ctl1.get_group_list() == [None, CURRENT_USER, None]
    assert path_ctl1.get_group_list(default_group='test') == ['test', CURRENT_USER, 'test']
    assert path_ctl2.get_group_list() == [None]


def test_path_user_list(path_ctl1, path_ctl2):
    assert path_ctl1.get_user_list() == [CURRENT_USER, None, 'root']
    assert path_ctl1.get_user_list(default_user='test') == [CURRENT_USER, 'test', 'root']
    assert path_ctl2.get_user_list() == [None]


def test_path_iter(path_ctl1, context):
    with pytest.raises(PathContextError):
        list(path_ctl1.iter_path())
    assert list(path_ctl1.iter_path(skip_context_errors=True)) == ['publish']
    assert list(path_ctl1.iter_path(skip_context_errors=True, full_path=True)) == ['/tmp/my_struct/shot/publish']
    assert list(path_ctl1.iter_path(context, full_path=True)) == ['/tmp/my_struct/example/shot/sh001/publish', '/tmp/my_struct/example/shot/sh001/publish/v015']
    assert list(path_ctl1.iter_path(context, full_path=True, dirs_only=False)) == ['/tmp/my_struct/example/shot/sh001/publish', '/tmp/my_struct/example/shot/sh001/publish/v015', '/tmp/my_struct/example/shot/sh001/publish/v015/sh001_v015.exr']


def test_path_values(path_ctl1, path_ctl2):
    assert path_ctl1.get_absolute() == '/tmp/my_struct/{PROJECT_NAME}/shot/{ENTITY_NAME}/publish/v{VERSION:03d}/{ENTITY_NAME}_v{VERSION:03d}.{EXT}'
    assert path_ctl1.get_relative() == '{PROJECT_NAME}/shot/{ENTITY_NAME}/publish/v{VERSION:03d}/{ENTITY_NAME}_v{VERSION:03d}.{EXT}'
    assert path_ctl1.get_short() == 'publish/v{VERSION:03d}/{ENTITY_NAME}_v{VERSION:03d}.{EXT}'
    assert path_ctl2.get_absolute() == '/tmp/my_struct/{PROJECT_NAME}/assets/{ENTITY_NAME}/models'
    assert path_ctl2.get_relative() == '{PROJECT_NAME}/assets/{ENTITY_NAME}/models'
    assert path_ctl2.get_short() == 'models'


def test_options_preset(tree):
    assert tree.get_path_instance('ASSET').options == {'path': '[ASSETS]/{ENTITY_NAME}', 'user': 'test', 'perm': '755'}


# I/O TESTS

def test_makedirs_tree(tree, context):
    tree.makedirs(context)


def test_makedirs_path(path_ctl1, context):
    path_ctl1.makedirs(context)
