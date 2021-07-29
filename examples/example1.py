from pathname import PNTree

path_list = dict(
    PROJECT={
        'path': '{PROJECT_NAME}'
    },
    CONFIG={
        'path': '[PROJECT]/.config',
        'groups': []
    },
    # SHOTS #########################################
    SHOTS={
        'path': '[PROJECT]/shots'
    },
    SEQUENCE={
        'path': '[SHOTS]/{SEQUENCE}',
    },
    SHOT={
        'path': '[SEQUENCE]/{ENTITY_NAME}',
    },
    SHOT_CAMERA={
        'path': '[SHOT]/camera'
    },
    SHOT_COMP={
        'path': '[SHOT]/comp',
    },
    SHOT_LIGHT={
        'path': '[SHOT]/light',
    },
    SHOT_FX={
        'path': '[SHOT]/fx',
    },
    SHOT_PLATES={
        'path': '[SHOT]/plates',
    },
    SHOT_REFS={
        'path': '[SHOT]/refs',
    },
    SHOT_SOUND={
        'path': '[SHOT]/sound',
    },
    SHOT_RENDER={
        'path': '[SHOT]/render',
    },
    SHOT_TEMP={
        'path': '[SHOT]/temp',
        'chmod': 0o777
    },
    SHOT_RENDER_PUBLISH={
        'path': '[SHOT_RENDER]/publish/v{VERSION:03d}/{ENTITY_NAME}_v{VERSION:03d}_{FRAME:05d}.{EXT}',
        'defaults': {'EXT': 'exr'}
    },
    SHOT_RENDER_TEMP={
        'path': '[SHOT_RENDER]/temp/{ENTITY_NAME}/{FILENAME}.{EXT}',
        'defaults': {'filename': 'datetime_name()', 'EXT': 'exr'}
    },
    SHOT_ANIMATION={
        'path': '[SHOT]/animation'
    },
    SHOT_ANIMATION_PUBLISH_SCENE={
        'path': '[SHOT_ANIMATION]/publish/scenes/v{VERSION:03d}/{SEQUENCE}_{ENTITY_NAME}_anim.{EXT}',
        'defaults': {'EXT': 'ma'}
    },
    SHOT_ANIMATION_PUBLISH_CACHE={
        'path': '[SHOT_ANIMATION]/publish/cache/v{VERSION:03d}/{SEQUENCE}_{ENTITY_NAME}_cache.{EXT}',
        'defaults': {'EXT': 'abc'}
    },
    SHOT_LIB={
        'path': '[SHOT]/lib',
    },
    # ASSETS #########################################
    ASSETS={
        'path': '[PROJECT]/assets',
    },
    ASSET={
        'path': '[ASSETS]/{ENTITY_NAME}',
    },
    ASSET_MODEL={
        'path': '[ASSET]/models'
    },
    ASSET_ANIMATION={
        'path': '[ASSET]/animation'
    },
    ASSET_RIGS={
        'path': '[ASSET]/rigs'
    },
    ASSET_TEXTURES={
        'path': '[ASSET]/textures',
    },
    ASSET_TEXTURE_PUBLISH={
        'path': '[ASSET_TEXTURES]/{VARIANT}/v{VERSION}/{FILENAME}.{EXT}',
        'defaults': {'VARIANT': 'main', 'EXT': 'exr'}
    },
    ASSET_LIB={
        'path': '[ASSET]/lib',
    },
    ASSET_RENDER={
        'path': '[ASSET]/render',
    },
    ASSET_REFS={
        'path': '[ASSET]/ref',
    },
    ASSET_TEMP={
        'path': '[ASSET]/temp',
        'chmod': 0o777
    }
)

context = dict(
    project_name='example',
    sequence='03s001',
    entity_name='03s001_0010',
    version=5,
    filename='example_file',
    variant='custom_char',
    frame=225
)

tree = PNTree(root_path='d:/projects', path_list=path_list)

tree.check_uniqueness_of_parsing(context)
# {'errors': {}, 'success': ['SHOT_FX', 'SHOT_COMP', 'ASSET_TEXTURES'...
tree.get_path_names()
# ('SHOT_FX', 'SHOT_COMP', 'ASSET_TEXTURES', 'ASSET_LIB', 'SHOTS'...
path = tree.get_path('SHOT', context)
# 'd:\\projects\\example\\shots\\03s001\\03s001_0010'
tree.parse(path)
# 'SHOT'
path2 = tree.get_path('SHOT_RENDER_PUBLISH', context)
tree.parse(path2)
# 'SHOT_RENDER_PUBLISH'
tree.parse(path2, with_variables=True)
# ('SHOT_RENDER_PUBLISH', {'project_name': 'example', 'entity_name': '03s001_0010',
# 'sequence': '03s001', 'frame': '00225', 'ext': 'exr', 'version': '005'})
