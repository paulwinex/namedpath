## NamedPath

This is a module which can help you to configure folder structure with named patterns. 
No more absolute paths in scripts, no more hard coding. 
With `namedpath` you can generate paths via names with variables context!

```python
import namedpath

# create list of patterns with inheritance
path_list = dict(
    PROJECT='{PROJECT_NAME}',
    SHOTS='[PROJECT]/shots',
    SHOT='[SHOTS]/{SHOT_NAME}',
    LAYOUT='[SHOT]/layout',
    LAYOUT_PUBLISH='[LAYOUT]/publish/{SHOT_NAME|lower()}_v{VERSION:04d}/{SHOT_NAME|lower()}.exr',
    RENDER='[SHOT]/render',
    RENDER_PUBLISH='[RENDER]/{VERSION:04d}/{FILE_NAME}_{FRAME}.{EXT}',
)
# create tree instance
tree = namedpath.NamedPathTree('/mnt/my_projects', path_list)
# define context
context = {
    'project_name': 'project1',
    'shot_name': 'sh01',
    'file_name': 'test_render',
    'version': 15,
    'ext': 'exr',
    'frame': '%04d'
}
# now you can generate the path
print(tree.get_path('RENDER_PUBLISH', context))
# /mnt/my_projects/project1/shots/sh01/render/0015/test_render_%04d.exr

# you can change any patterns and no need change the code after that
path_list['RENDER_PUBLISH'] = '[RENDER]/publish/v{VERSION:05d}/{SHOT_NAME}_rnd_{FRAME}.{EXT}'
tree = namedpath.NamedPathTree('/mnt/my_projects', path_list)
print(tree.get_path('RENDER_PUBLISH', context))
# /home/username/my_projects/project1/shots/sh01/render/publish/v00015/sh01_rnd_%04d.exr
```

- Any pattern can be inherited from another pattern.

- Each structure can have a different pattern set, but it will work with the same code.

- Supports generic string formatting and string method calls.

- Creates a folder structure with context or partial context.

```python
# formatting
pat1 = '[PARENT]/{VARIABLE:04d}'
# string methods
pat2 = '[PARENT]/{VARIABLE|strip()|upper()}'
# string methods with arguments
pat3 = '[PARENT]/{VARIABLE|center(10, "_")}'
```

- Transfer one file tree to other

You can remap one file structure to other using method `NamedPathTree.transfer_to`

```python
path_list1 = dict(
    PROJECT='{PROJECT_NAME}',
    CONFIG={
        'path': '[PROJECT]/.config'
    },
    SHOTS={
        'path': '[PROJECT]/shots',
    },

    SHOT={
        'path': '[SHOTS]/{ENTITY_NAME}/{ENTITY_NAME}{FRAME:04d}.{EXT}',
        'defaults': {'EXT': 'exr', "FRAME": ""},
        'prefix': {'FRAME': "-"},
        'types': {'FRAME': 'int'}
    },
)
path_list2 = dict(
    PRJ='{PROJECT}',
    CONF={
        'path': '[PRJ]/.config'
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

pattern_names_map = dict(
    PROJECT='PRJ',
    CONFIG='CONF',
    SHOTS='SHTS',
    SHOT='SHT',
)
context_map = dict(
    PROJECT_NAME='PROJECT',
    ENTITY_NAME='OBJ_NAME',
    FRAME='FRM',
    EXT='FILETYPE',
)

tree1 = NamedPathTree('/tmp/projects1', path_list1)
tree2 = NamedPathTree('/tmp/projects2', path_list2)
result = tree1.transfer_to(tree2, pattern_names_map, context_map)
pprint(result)

# >>> {'remapped_paths': [{'new_path': '/tmp/projects2/prj1',
# >>>                      'old_path': '/tmp/projects1/prj1'},
# >>>                     {'new_path': '/tmp/projects2/prj1/.config',
# >>>                      'old_path': '/tmp/projects1/prj1/.config'},
# >>>                     {'new_path': '/tmp/projects2/prj1/shots',
# >>>                      'old_path': '/tmp/projects1/prj1/shots'},
# >>>                     {'new_path': '/tmp/projects2/prj1/shots/prod/box001.exr',
# >>>                      'old_path': '/tmp/projects1/prj1/shots/box/box0001.exr'},
# >>>                     {'new_path': '/tmp/projects2/prj1/shots/prod/box002.exr',
# >>>                      'old_path': '/tmp/projects1/prj1/shots/box/box0002.exr'},
# >>>                     {'new_path': '/tmp/projects2/prj1/shots/prod/cube001.exr',
# >>>                      'old_path': '/tmp/projects1/prj1/shots/cube/cube_0001.exr'},
# >>>                     {'new_path': '/tmp/projects2/prj1/shots/prod/cube002.exr',
# >>>                      'old_path': '/tmp/projects1/prj1/shots/cube/cube_0002.exr'}],
# >>>  'skipped_paths': ['/tmp/projects1/prj1/shots/box',
# >>>                    '/tmp/projects1/prj1/shots/cube']}


```

Now you can move or copy all files to the new project structure!

- Optional arguments

You can use special syntax to add optional arguments to the pattern.

```python
path_list = dict(
    MY_PATH='{root}/{filename}<_{suffix}>.{ext}',
   
)
tree = NamedPathTree('/tmp', path_list)
tree.get_path("MY_PATH", {"root": "/store", "filename": "my_file", "ext": "png"})
# /tmp/store/my_file.png
tree.get_path("MY_PATH", {"root": "/store", "filename": "my_file", "ext": "png", "suffix": "demo"})
# /tmp/store/my_file_demo.png

```

All text inside `<>` will remove if variable `suffix` not exists in the context



TODO:

- set permissions and owner
- transfer tool

### Alternatives

https://gitlab.com/4degrees/lucidity
