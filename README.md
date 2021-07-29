## PathName

This is a module which can helps you to configure folder structure with patterns. No more absolute paths, 
no more hard coding. With `pathname` you can use paths via names with variables context!

```python
import pathname

path_list = dict(
    PROJECT='{PROJECT_NAME}',
    SHOTS='[PROJECT]/shots',
    SHOT='[SHOTS]/{SHOT_NAME}',
    LAYOUT='[SHOT]/layout',
    LAYOUT_PUBLISH='[LAYOUT]/publish/{SHOT_NAME|lower}_v{VERSION:04d}/{SHOT_NAME|lower}.exr',
    RENDER='[SHOT]/render',
    RENDER_PUBLISH='[RENDER]/{VERSION:04d}/{FILE_NAME}_{FRAME}.{EXT}',
)
tree = pathname.PNTree('~/my_projects', path_list)
context = {
    'project_name': 'project1',
    'shot_name': 'sh01',
    'file_name': 'test_render',
    'version': 15,
    'ext': 'exr',
    'frame': '%04d'
}
print(tree.get_path('RENDER_PUBLISH', context))
# C:\Users\username\my_projects\project1\shots\sh01\render\0015\test_render_%04d.exr
```

Now you can change the patterns and no need change the code.

```python
path_list['RENDER_PUBLISH'] = '[RENDER]/publish/v{VERSION:05d}/{SHOT_NAME}_rnd_{FRAME}.{EXT}'
tree = pathname.PNTree('~/my_projects', path_list)
print tree.get_path('RENDER_PUBLISH', context)
# C:\Users\username\my_projects\project1\shots\sh01\render\publish\v00015\sh01_rnd_%04d.exr
```

Each structure can have different pattern set, but it will work with same code.
