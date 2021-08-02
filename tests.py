import os
from pathname import PNTree
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
    return PNTree(ROOT, patterns)


def test_unique_patterns(tree, context):
    tree.check_uniqueness_of_parsing(context)


def test_pattern_creation(tree, patterns):
    assert set(tree.get_path_names()) == set(patterns.keys())


def test_paths_solving(tree, context):
    assert tree.get_path('PROJECT', context) == os.path.normpath(ROOT + '\example')
    p1 = tree.get_path('SHOT_PUBLISH', context)
    p2 = os.path.normpath(os.path.join(ROOT, r'example\shot\sh001\publish\v015\sh001_v015.exr'))
    assert p1 == p2, '{} != {}'.format(p1, p2)


def test_parsing(tree, context):
    path1 = tree.get_path('SHOT', context)
    name = tree.parse(path1)
    assert name == 'SHOT'
