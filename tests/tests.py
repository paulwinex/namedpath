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
        PROJECT_NAME='example',
        ENTITY_NAME='sh001',
        VERSION=15,
        EXT='exr'
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

# =======================================================

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
    assert tree.root == '/tmp/my_struct'
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
    assert pat == r'^(?P<PROJECT_NAME>[^/\\]+)/shot/(?P<ENTITY_NAME>[^/\\]+)/publish/v(?P<VERSION>[^/\\]+)/[^/\\]+_v[^/\\]+\.(?P<EXT>[^/\\]+)$'


# def test_path_permissions_list(path_ctl1):
#     assert path_ctl1.get_permission_list() == [493, 493, 493]
#     assert path_ctl1.get_permission_list(default_permission=0o775) == [509, 509, 509]


# def test_path_group_list(path_ctl1, path_ctl2):
#     assert path_ctl1.get_group_list() == [None, CURRENT_USER, None]
#     assert path_ctl1.get_group_list(default_group='test') == ['test', CURRENT_USER, 'test']
#     assert path_ctl2.get_group_list() == [None]


# def test_path_user_list(path_ctl1, path_ctl2):
#     assert path_ctl1.get_user_list() == [CURRENT_USER, None, 'root']
#     assert path_ctl1.get_user_list(default_user='test') == [CURRENT_USER, 'test', 'root']
#     assert path_ctl2.get_user_list() == [None]


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


def test_context_value_type(tree, context):
    assert tree.parse('/tmp/my_struct/example/shot/sh001/publish/v015/sh001_v015.exr', with_context=True)[1]['VERSION'] == 15



@pytest.fixture()
def path_list1():
    return dict(
    PROJECT='{PROJECT_NAME}',
    CONFIG={
        'path': '[PROJECT]/.config'
    },
    SHOTS={
        'path': '[PROJECT]/shots',
        'symlink_to': '{MNT_SHOTS}'
    },
    SHOT={
        'path': '[SHOTS]/{ENTITY_NAME}/{ENTITY_NAME}{FRAME:04d}.{EXT}',
        'defaults': {'EXT': 'exr', "FRAME": ""},
        'prefix': {'FRAME': "-"},
        'types': {'FRAME': 'int'}
    },
)

@pytest.fixture()
def path_list2():
    return dict(
    PRJ='{PROJECT}',
    CONF={
        'path': '[PRJ]/.conf'
    },
    SHTS={
        'path': '[PRJ]/shots',
    },
    SHT={
            'path': '[SHTS]/prod/{OBJ_NAME}{FRM:03d}.{FILETYPE}',
            'defaults': {'FILETYPE': 'exr', "FRM": ""},
            'prefix': {'FRM': "_"},
            'types': {'FRM': 'int'}
        },
)

@pytest.fixture()
def pattern_names_map():
    return dict(
        PROJECT='PRJ',
        CONFIG='CONF',
        SHOTS='SHTS',
        SHOT='SHT',
    )

@pytest.fixture()
def context_map():
    return dict(
        PROJECT_NAME='PROJECT',
        ENTITY_NAME='OBJ_NAME',
        FRAME='FRM',
        EXT='FILETYPE',
    )


# def test_transfer_structures(path_list1, path_list2, pattern_names_map, context_map):
#     t1 = NamedPathTree('/tmp/projects1', path_list1)
#     t2 = NamedPathTree('/tmp/projects2', path_list2)
#     res = t1.transfer_to(t2, pattern_names_map, context_map)
#     expected_res = {'remapped_paths': [{'old_path': '/tmp/projects1/prj1', 'new_path': '/tmp/projects2/prj1'}, {'old_path': '/tmp/projects1/prj1/.config', 'new_path': '/tmp/projects2/prj1/.conf'}, {'old_path': '/tmp/projects1/prj1/shots', 'new_path': '/tmp/projects2/prj1/shots'}, {'old_path': '/tmp/projects1/prj1/shots/box/box0001.exr', 'new_path': '/tmp/projects2/prj1/shots/prod/box001.exr'}, {'old_path': '/tmp/projects1/prj1/shots/box/box0002.exr', 'new_path': '/tmp/projects2/prj1/shots/prod/box002.exr'}, {'old_path': '/tmp/projects1/prj1/shots/cube/cube_0001.exr', 'new_path': '/tmp/projects2/prj1/shots/prod/cube001.exr'}, {'old_path': '/tmp/projects1/prj1/shots/cube/cube_0002.exr', 'new_path': '/tmp/projects2/prj1/shots/prod/cube002.exr'}], 'skipped_paths': ['/tmp/projects1/prj1/shots/box', '/tmp/projects1/prj1/shots/cube']}
#     assert res == expected_res


# I/O TESTS

# def test_makedirs_tree(tree, context):
#     tree.makedirs(context)


# def test_makedirs_path(path_ctl1, context):
#     path_ctl1.makedirs(context)
