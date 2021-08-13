from namedpath import NamedPathTree

path_list = dict(
    PROJECT='{PROJECT_NAME}',       # simple pattern
    CONFIG={                        # detailed pattern
        'path': '[PROJECT]/.config'
    },
    # SHOTS #########################################
    SHOTS={
        'path': '[PROJECT]/shots',
        'symlink_to': '{MNT_SHOTS}'
    },
    SEQUENCE='[SHOTS]/{SEQUENCE}',
    SHOT='[SEQUENCE]/{ENTITY_NAME}',
    SHOT_CAMERA='[SHOT]/camera',
    SHOT_COMP='[SHOT]/comp',
    SHOT_LIGHT='[SHOT]/light',
    SHOT_FX='[SHOT]/fx',
    SHOT_PLATES='[SHOT]/plates',
    SHOT_REFS='[SHOT]/refs',
    SHOT_SOUND='[SHOT]/sound',
    SHOT_RENDER='[SHOT]/render',
    SHOT_TEMP={
        'path': '[SHOT]/temp',
        'perm': 0o777
    },
    SHOT_RENDER_PUBLISH={
        'path': '[SHOT_RENDER]/publish/v{VERSION:03d}/{ENTITY_NAME}_v{VERSION:03d}_{FRAME:05d}.{EXT}',
        'defaults': {'EXT': 'exr'},

        'perm': [
            0o755,   # access mode for "publish" dir
            None,    # from default
            '0o644'    # access mode for publish file
        ],
        'users':
            ['root',    # owner of "publish" dir
             None,      # default (current user)
             '{USER}'   # owner of file (from context)
             ],
        'groups': 'root'     # group "root" for all dirs and files
    },
    SHOT_RENDER_TEMP={
        'path': '[SHOT_RENDER]/temp/{ENTITY_NAME}/{FILENAME}.{EXT}',
        'defaults': {'filename': 'datetime_name()', 'EXT': 'exr'},
        'groups': ['root', 'admin']
    },
    SHOT_ANIMATION='[SHOT]/animation',
    SHOT_ANIMATION_PUBLISH_SCENE={
        'path': '[SHOT_ANIMATION]/publish/scenes/v{VERSION:03d}/{SEQUENCE}_{ENTITY_NAME}_anim.{EXT}',
        'defaults': {'EXT': 'ma'}
    },
    SHOT_ANIMATION_PUBLISH_CACHE={
        'path': '[SHOT_ANIMATION]/publish/cache/v{VERSION:03d}/{SEQUENCE}_{ENTITY_NAME}_cache.{EXT}',
        'defaults': {'EXT': 'abc'}
    },
    SHOT_LIB='[SHOT]/lib',
    # ASSETS #########################################
    ASSETS='[PROJECT]/assets',
    ASSET='[ASSETS]/{ENTITY_NAME}',
    ASSET_MODEL='[ASSET]/models',
    ASSET_ANIMATION='[ASSET]/animation',
    ASSET_RIGS='[ASSET]/rigs',
    ASSET_TEXTURES='[ASSET]/textures',
    ASSET_TEXTURE_PUBLISH={
        'path': '[ASSET_TEXTURES]/{VARIANT}/v{VERSION}/{FILENAME}.{EXT}',
        'defaults': {'VARIANT': 'main', 'EXT': 'exr'}
    },
    ASSET_LIB='[ASSET]/lib',
    ASSET_RENDER='[ASSET]/render',
    ASSET_REFS='[ASSET]/ref',
    ASSET_TEMP={
        'path': '[ASSET]/temp',
        'perm': 0o777
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

tree = NamedPathTree(root_path='d:/projects', path_list=path_list, default_group='paul')
tree.check_uniqueness_of_parsing(context)
# {'errors': {}, 'success': ['SHOT_FX', 'SHOT_COMP', 'ASSET_TEXTURES'...
tree.get_path_names()
# ('SHOT_FX', 'SHOT_COMP', 'ASSET_TEXTURES', 'ASSET_LIB', 'SHOTS'...
path = tree.get_path('SHOT', context)
# 'd:\\projects\\example\\shots\\03s001\\03s001_0010'
tree.parse(path)
# 'SHOT'
path2 = tree.get_path('SHOT_RENDER_PUBLISH')
tree.parse(path2)
# 'SHOT_RENDER_PUBLISH'
tree.parse(path2, with_variables=True)
# ('SHOT_RENDER_PUBLISH', {'project_name': 'example', 'entity_name': '03s001_0010',
# 'sequence': '03s001', 'frame': '00225', 'ext': 'exr', 'version': '005'})
