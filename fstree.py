# coding=utf-8
from __future__ import print_function, absolute_import
from os.path import join, normpath, exists
import copy
import logging
import re
import json
import sys

logger = logging.getLogger(__name__)

if sys.version_info.major > 2:
    unicode = type


class FSTree(object):
    """
    Класс, отвечающий за всю структуру. Содержит и управляет полным список путей.
    """

    def __init__(self, root_path, path_list):
        self._root_path = root_path
        self._scope = {}
        self._init_scope(path_list)

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<FSTree "{}">'.format(self.path)

    @property
    def path(self):
        """
        Корневой путь структуры

        Returns
        -------
        str
        """
        return self._root_path

    def _init_scope(self, path_list):
        """Создание инстансов паттернов"""
        for path_name, options in path_list.items():
            if isinstance(options, str):
                options = dict(path=options)
            self._scope[path_name] = FSPath(path_name, options, self._scope)

    def get_path(self, name, context, create=False):
        """
        Получить полный путь по имени и контексту

        Parameters
        ----------
        name: str
            Имя паттерна
        context: dict
            Контекст ресолвинга переменных
        create: bool
            Создать запрашиваемый путь

        Returns
        -------
        str
        """
        ctl = self.get_path_instance(name)    # type: FSPath
        path = normpath(join(self.path, ctl.solve(context).lstrip('\\/')))
        if create and not exists(path):
            ctl.makedirs()
        return path

    def get_raw_path(self, name):
        return self.get_path_instance(name).get_full_path()

    def get_raw_pattern(self, name):
        return self.get_path_instance(name).path

    def get_path_instance(self, name):
        """
        Инстанс класса управляющего конкретным паттерном

        Parameters
        ----------
        name: str

        Returns
        -------
        FSPath
        """
        try:
            return self._scope[name]
        except KeyError:
            raise PathNameError('Pattern named {} not found'.format(name))

    def get_path_names(self):
        """
        Список имён паттернов текущей структуры

        Returns
        -------
        tuple
        """
        return tuple(self._scope.keys())

    def parse(self, path, with_variables=False):
        """
        Определение имени пути по готовому пути

        Parameters
        ----------
        path
        with_variables

        Returns
        -------
        list
        """
        match_names = []
        for name, p in self._scope.items():  # type: FSPath
            pattern = p.as_regex(self.path)
            m = re.match(pattern, path, re.IGNORECASE)
            if m:
                match_names.append((name, m.groupdict()))
        if len(match_names) > 1:
            raise MultiplePatternMatchError(', '.join([x[0] for x in match_names]))
        if not match_names:
            raise NoPatternMatchError
        if with_variables:
            return match_names[0]
        else:
            return match_names[0][0]

    def check_uniqueness_of_parsing(self, full_context):
        """
        Поверка уникальности путей, то есть возможность однозначно найти имя по готовому пути.
        Для проверки требуется контекст, который подойдет для всех паттернов.
        Эта проверка используется на этапе разработки структуры.

        Parameters
        ----------
        full_context: dict

        Returns
        -------
        dict
        """
        result = dict(
            errors={},
            success=[]
        )
        for name in self.get_path_names():
            path = self.get_path(name, full_context)
            try:
                parsed_name = self.parse(path)
            except NoPatternMatchError as e:
                print(str(e))
                result['errors'][name] = str(e)
            except MultiplePatternMatchError as e:
                print(str(e))
                result['errors'][name] = str(e)
            else:
                if parsed_name != name:
                    result['errors'][name] = 'Generated and parsed names not match: {} -> {}'.format(name, parsed_name)
                else:
                    result['success'].append(name)
        print('Total patterns:', len(self._scope))
        print('Success parsing:', len(result['success']))
        print('Errors:', len(result['errors']))
        return result

    def transfer_to(self, other_tree, names_map=None, move=True, cleanup=True):
        """
        Перемещение файлов из одной структуры в другую.
        Состав имён путей должен совпадать. Если именя различаются можно указать карту переименования.

        Parameters
        ----------
        other_tree: FSTree
            Структура в которую следует переместить файлы
        names_map: dict
            Картка соответствия ключей
        move: bool
            Копировать или перемещать
        cleanup: bool
            Удалить старую структуру
        Returns
        -------
        dict
        """
        raise NotImplementedError

    def check_paths_attributes(self, fix=False):
        """
        Рекурсивный поиск всех имеющихся директорий в структуре
        и проверка их атрибутов в соответствии с опциями из конфига
        """


class FSPath(object):
    default_chmod = 0o755

    def __init__(self, name, options, scope, **kwargs):
        self.name = name
        self.options = options
        self._scope = scope
        self.kwargs = kwargs

    def __str__(self):
        return self.path

    def __repr__(self):
        return '<FSPath %s>' % self.path

    @property
    def path(self):
        return self.options['path']

    def solve(self, context):
        """
        Ресолвинг пути из паттерна используя контекст

        Parameters
        ----------
        context: dict

        Returns
        -------
        str
        """
        path = self.get_full_path()
        return self.expand_variables(path, context)

    def expand_variables(self, text, variables):
        """
        Ресолвинг переменных

        Parameters
        ----------
        text: str
        variables: dict

        Returns
        -------
        str
        """
        ctx = copy.deepcopy(variables)
        for k, v in self.options.get('defaults', {}).items():
            ctx.setdefault(k, v)
        return CustomFormatString(text).format(**{k.upper(): v for k, v in ctx.items()})

    def get_full_path(self):
        """
        Полный путь включая родительские паттерны

        Returns
        -------

        """
        par = self.get_parent()
        if par:
            return normpath(join(
                par.get_full_path(),
                self.relative())
            )
        else:
            return self.path

    def relative(self):
        return self.path.split(']', 1)[-1].lstrip('\\/')

    def variables(self):
        """
        Извлечение имён переменных из пути

        Returns
        -------
        list
        """
        variables = []
        for val in re.findall(r"{(.*?)}", self.get_full_path()):
            variables.append(val.split(':')[0])
        return variables

    def get_parent(self):
        match = re.search(r"^\[(\w+)]/?(.*)", self.path)
        if match:
            try:
                return self._scope[match.group(1)]
            except KeyError:
                raise PathNameError

    def as_pattern(self, prefix=None):
        """
        Паттерн пути в виде glob-паттерна

        Parameters
        ----------
        prefix: str
            Корневой путь если есть. По умолчанию путь релятивный.

        Returns
        -------
        str
        """
        path = self.get_full_path()
        if prefix:
            path = normpath(join(prefix, path.lstrip('\\/')))
        return re.sub(r"{.*?}", '*', path)

    def as_regex(self, prefix=None, named_values=True):
        """
        Паттерн пути в виде regex-паттерна

        Parameters
        ----------
        prefix: str
            Корневой путь если есть. По умолчанию путь релятивный.
        named_values: bool

        Returns
        -------
        str
        """
        path = self.get_full_path()
        if prefix:
            path = normpath(join(prefix, path.lstrip('\\/')))

        names = []

        def get_subpattern(match):
            v = match.group(0)
            name = v.strip('{}').split(':')[0]
            if name in names:
                return r'[\w\d]+'
            names.append(name)
            return r'(?P<%s>[\w\d\s:|"\'-]+)' % name.lower().split('|')[0].split(':')[0]
        pattern = re.sub(r"{.*?}", get_subpattern, path.replace('\\', '\\\\'))
        pattern = '^%s$' % pattern
        return pattern

    @property
    def chmod(self):
        return self.options.get('chmod', self.default_chmod)

    @property
    def groups(self):
        return self.options.get('chmod', [])

    @property
    def chown(self):
        return self.options.get('chown', [])

    def makedirs(self):
        pass


class CustomFormatString(str):
    """
    Класс с дополнительной обработкой строки с помощью стандартных методов строки.
    Класс может быть использован как обычный объект строки.
    Можно указывать несколько методов через символ |
    Аргументы методов следует указывать после имени метода через знак :
    Аргументы должны быть в формате JSON через пробел

    >>> CustomFormatString('NAME_{value|upper}').format(value='e01s03')
    >>> 'NAME_E01S03'
    Можно указывать несоклько методов
    >>> CustomFormatString('name_{value|lower|strip}').format(value=' E01S03  ')
    >>> 'name_e01s03'
    Аргументы методов
    >>> CustomFormatString('{value|strip|center:10 "-"}').format(value=' E01S03  ')
    >>> '--E01S03--'

    """
    sep = '|'

    def format(self, *args, **kwargs):
        context = copy.deepcopy(kwargs)
        variables = re.findall(r"({([\w\d%s]+([:\w\d\s.,'\"-_|]+)?)})" % self.sep, self)
        for full_pat, expr, _ in variables:
            # break
            if self.sep in expr:
                v, methods = expr.split(self.sep, 1)
                methods = methods.split(self.sep)
                self = CustomFormatString(str.replace(self, full_pat, '{%s}' % v))
                val = context.get(v.split(':')[0])
                if not val:
                    raise ValueError('No value {} in {}'.format(v, context.keys()))
                for m in methods:
                    # break
                    cmd, args = self.parse_args(m)
                    val = getattr(val, cmd)(*args)
                context[v] = val
        return str.format(self, **context)
        # return str.format(self, *args, **context)

    def parse_args(self, method):
        if not isinstance(method, str):
            method = method.encode()
        if ':' in method:
            cmd, _args = method.split(':', 1)
            args = [x.strip() for x in self.split_args(_args)]
            args = list(map(json.loads, args))
            args = [x.encode() if isinstance(x, unicode) else x for x in args]
        else:
            cmd = method
            args = ()
        return cmd, args

    def split_args(self, args):
        args_array = [x for x in re.split(r"('.*?'|\".*?\"|\S+)", args) if x.strip()]
        return args_array


class PathNameError(Exception):
    pass


class MultiplePatternMatchError(Exception):
    pass


class NoPatternMatchError(Exception):
    pass

