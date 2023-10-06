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
                SHOT_REFS='[SHOT]/refs',
                SHOT_PLATES='[SHOT]/plates',            
                SHOT_CAMERA='[SHOT]/camera',
                SHOT_COMP='[SHOT]/comp',
                SHOT_LIGHT='[SHOT]/light',
                SHOT_FX='[SHOT]/fx',
                SHOT_SOUND='[SHOT]/sound',
                SHOT_RENDER='[SHOT]/render',
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
                SHOT_TEMP={
                    'path': '[SHOT]/temp',
                    'perm': 0o777
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

tree = NamedPathTree(root_path='/mnt/projects', path_list=path_list, default_group='paul')

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

tree.show_tree()
'''
ROOT: /mnt/projects
==================================================
                       PROJECT|/{PROJECT_NAME}
                        ASSETS|--/assets
                         ASSET|----/{ENTITY_NAME}
               ASSET_ANIMATION|------/animation
                     ASSET_LIB|------/lib
                   ASSET_MODEL|------/models
                    ASSET_REFS|------/ref
                  ASSET_RENDER|------/render
                    ASSET_RIGS|------/rigs
                    ASSET_TEMP|------/temp
                ASSET_TEXTURES|------/textures
         ASSET_TEXTURE_PUBLISH|--------/{VARIANT}/v{VERSION}/{FILENAME}.{EXT}
                        CONFIG|--/.config
                         SHOTS|--/shots
                      SEQUENCE|----/{SEQUENCE}
                          SHOT|------/{ENTITY_NAME}
                SHOT_ANIMATION|--------/animation
  SHOT_ANIMATION_PUBLISH_CACHE|----------/publish/cache/v{VERSION:03d}/{SEQUENCE}_{ENTITY_NAME}_cache.{EXT}
  SHOT_ANIMATION_PUBLISH_SCENE|----------/publish/scenes/v{VERSION:03d}/{SEQUENCE}_{ENTITY_NAME}_anim.{EXT}
                   SHOT_CAMERA|--------/camera
                     SHOT_COMP|--------/comp
                       SHOT_FX|--------/fx
                      SHOT_LIB|--------/lib
                    SHOT_LIGHT|--------/light
                   SHOT_PLATES|--------/plates
                     SHOT_REFS|--------/refs
                   SHOT_RENDER|--------/render
           SHOT_RENDER_PUBLISH|----------/publish/v{VERSION:03d}/{ENTITY_NAME}_v{VERSION:03d}_{FRAME:05d}.{EXT}
              SHOT_RENDER_TEMP|----------/temp/{ENTITY_NAME}/{FILENAME}.{EXT}
                    SHOT_SOUND|--------/sound
                     SHOT_TEMP|--------/temp
==================================================
'''
