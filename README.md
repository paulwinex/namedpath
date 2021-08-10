## NamedPath

This is a module which can helps you to configure folder structure with named patterns. 
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
tree = namedpath.PNTree('~/my_projects', path_list)
# define context
context = {
    'project_name': 'project1',
    'shot_name': 'sh01',
    'file_name': 'test_render',
    'version': 15,
    'ext': 'exr',
    'frame': '%04d'
}
# now you can generate path
print(tree.get_path('RENDER_PUBLISH', context))
# C:\Users\username\my_projects\project1\shots\sh01\render\0015\test_render_%04d.exr

# you can change any patterns and no need change the code after that
path_list['RENDER_PUBLISH'] = '[RENDER]/publish/v{VERSION:05d}/{SHOT_NAME}_rnd_{FRAME}.{EXT}'
tree = namedpath.PNTree('~/my_projects', path_list)
print tree.get_path('RENDER_PUBLISH', context)
# C:\Users\username\my_projects\project1\shots\sh01\render\publish\v00015\sh01_rnd_%04d.exr
```

- Any  pattern can be inherited from other pattern

- Each structure can have different pattern set, but it will work with same code.

- Support generic string formatting and string methods call

```python
# formatting
pat1 = '[PARENT]/{VARIABLE:04d}'
# string methods
pat2 = '[PARENT]/{VARIABLE|strip()|upper()}'
# string methods with arguments
pat3 = '[PARENT]/{VARIABLE|center(10, "_")}'
```

-------
Project still underdeveloped
