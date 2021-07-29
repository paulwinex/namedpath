import os
from fstree import FSTree
import pytest
import tempfile

ROOT = os.path.join(tempfile.gettempdir(), 'my_struct')


@pytest.fixture()
def patterns():
    return dict(
        PROJECT='{PROJECT}',
        SHOTS='[PROJECT]/shot',
        SHOT='[SHOTS]/{ENTITY_NAME}',
        SHOT_PUBLISH='[SHOT]/publish/v{VERSION:03d}/{ENTITY_NAME}_v{VERSION:03d}.{EXT}',
        ASSETS='[PROJECT]/assets',
        ASSET='[ASSETS]/{ENTITY_NAME}',
        ASSSET_MODELS='[ASSET]/models'
    )


@pytest.fixture()
def context():
    return dict(
        project='example',
        entity_name='sh001',
        version=15,
        ext='exr'
    )


@pytest.fixture()
def tree(patterns):
    return FSTree(ROOT, patterns)


def test_unique_patterns(tree, context):
    tree.check_uniqueness_of_parsing(context)


def test_pattern_creation(tree, patterns):
    assert tree.get_path_names() == tuple(patterns.keys())


def test_paths_solving(tree, context):
    assert tree.get_path('PROJECT', context) == os.path.normpath(ROOT + '\example')
    assert tree.get_path('SHOT_PUBLISH', context) == os.path.normpath(ROOT + r'example\shot\sh001\publish\v015\sh001_v015.exr')


def test_parsing(tree, context):
    path1 = tree.get_path('SHOT', context)
    name = tree.parse(path1)
    assert name == 'SHOT'
